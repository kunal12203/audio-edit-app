import os
import json
import uuid
import logging
from importlib import metadata # To correctly check package version
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
from yt_dlp import YoutubeDL
from pydub import AudioSegment
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)
load_dotenv()

# --- Helper Functions ---

def convert_time_to_ms(time_str: str):
    parts = time_str.split(':')
    minutes = int(parts[0])
    seconds = int(parts[1])
    return (minutes * 60 + seconds) * 1000

def search_youtube_for_url(song_name: str):
    try:
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            logger.error("YOUTUBE_API_KEY environment variable not set.")
            return None
        logger.info(f"Searching YouTube with API for '{song_name}'...")
        youtube = build('youtube', 'v3', developerKey=api_key)
        request = youtube.search().list(q=song_name, part='snippet', type='video', maxResults=1)
        response = request.execute()
        if response['items']:
            video_id = response['items'][0]['id']['videoId']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            logger.info(f"Found video URL via API: {video_url}")
            return video_url
        else:
            logger.warning(f"No results found for '{song_name}' using API.")
            return None
    except HttpError as e:
        logger.error(f"An HTTP error {e.resp.status} occurred: {e.content}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"An error occurred during YouTube API search for '{song_name}'", exc_info=True)
        return None

def download_audio_from_youtube(url: str, output_path="."):
    try:
        logger.info(f"Starting download from URL: {url}")
        output_template = os.path.join(output_path, '%(title)s.%(ext)s')
        ydl_opts = {
            'format': 'm4a/bestaudio/best', 'outtmpl': output_template,
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            'noplaylist': True,
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            base, _ = os.path.splitext(filename)
            mp3_filepath = base + '.mp3'
            if os.path.exists(mp3_filepath):
                logger.info(f"Successfully downloaded and converted to: {mp3_filepath}")
                return mp3_filepath
    except Exception as e:
        logger.error(f"An error occurred during download from {url}", exc_info=True)
        return None

def parse_prompt_with_openai(prompt: str):
    client = OpenAI()
    system_prompt = """
    You are an intelligent assistant that parses user requests for audio editing.
    Your task is to extract this information and return ONLY a valid JSON object.
    The JSON structure should be:
    {
      "clips": [
        {"name": "a_unique_clip_name", "song_name": "The song for this clip", "start": "MM:SS", "end": "MM:SS"}
      ],
      "sequence": ["an", "ordered", "list", "of", "clip", "names"]
    }
    Infer clip names and song titles accurately from the user's prompt.
    Ensure start/end times are always in "MM:SS" format.
    """
    logger.info("Sending prompt to OpenAI for processing...")
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    response_content = response.choices[0].message.content
    logger.info("OpenAI responded successfully.")
    return json.loads(response_content)

# --- FastAPI App setup ---
app = FastAPI()
jobs = {}
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
if not os.path.exists("output"):
    os.makedirs("output")
app.mount("/output", StaticFiles(directory="output"), name="output")

class PromptRequest(BaseModel):
    prompt: str
class JobResponse(BaseModel):
    job_id: str
class StatusResponse(BaseModel):
    status: str
    file_url: str | None = None

# --- Background Task Logic ---
def run_multi_song_processing(prompt: str, job_id: str):
    downloaded_files = []
    logger.info(f"Starting audio processing for job_id: {job_id}")
    try:
        jobs[job_id]["status"] = "parsing_prompt"
        parsed_data = parse_prompt_with_openai(prompt)
        if not parsed_data or "clips" not in parsed_data:
            raise ValueError("Failed to parse prompt with OpenAI.")

        processed_clips = {}
        downloaded_songs = {}
        
        for i, clip_info in enumerate(parsed_data["clips"]):
            song_name = clip_info["song_name"]
            clip_name = clip_info["name"]
            jobs[job_id]["status"] = "searching_youtube"
            
            if song_name in downloaded_songs:
                audio_file_path = downloaded_songs[song_name]
            else:
                song_url = search_youtube_for_url(song_name)
                if not song_url: raise ValueError(f"Could not find '{song_name}'")
                jobs[job_id]["status"] = "downloading_audio"
                audio_file_path = download_audio_from_youtube(song_url, output_path="output")
                if not audio_file_path: raise ValueError(f"Failed to download '{song_name}'")
                downloaded_songs[song_name] = audio_file_path
                downloaded_files.append(audio_file_path)

            jobs[job_id]["status"] = "processing_audio"
            logger.info(f"Trimming clip '{clip_name}' from '{song_name}'")
            sound = AudioSegment.from_mp3(audio_file_path)
            start_ms = convert_time_to_ms(clip_info['start'])
            end_ms = convert_time_to_ms(clip_info['end'])
            trimmed_clip = sound[start_ms:end_ms]
            processed_clips[clip_name] = trimmed_clip

        # DEBUG: Check the installed version of pydub correctly
        logger.info(f"Using pydub version: {metadata.version('pydub')}")

        logger.info("Merging all processed clips with a crossfade...")
        CROSSFADE_DURATION_MS = 1500

        sequence_to_merge = [processed_clips[name] for name in parsed_data["sequence"] if name in processed_clips]
        if not sequence_to_merge:
            raise ValueError("No valid clips found to merge.")

        final_audio = sequence_to_merge[0]
        for next_clip in sequence_to_merge[1:]:
            final_audio = final_audio.crossfade(next_clip, duration=CROSSFADE_DURATION_MS)

        output_filename = f"output/{job_id}.mp3"
        final_audio.export(output_filename, format="mp3")
        logger.info(f"Final audio saved to {output_filename}")
        jobs[job_id]["status"] = "complete"
        jobs[job_id]["file_url"] = f"/{output_filename}"

    except Exception as e:
        logger.error(f"Job {job_id} failed", exc_info=True)
        jobs[job_id]["status"] = "failed"
    finally:
        logger.info(f"Cleaning up {len(downloaded_files)} source file(s) for job {job_id}.")
        for file_path in downloaded_files:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError as e:
                    logger.warning(f"Error deleting file {file_path}: {e}")

# --- API Endpoints ---
@app.post("/generate", response_model=JobResponse)
async def generate_audio(request: PromptRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "pending", "file_url": None}
    background_tasks.add_task(run_multi_song_processing, request.prompt, job_id)
    logger.info(f"Job created with ID: {job_id}")
    return {"job_id": job_id}

@app.get("/status/{job_id}", response_model=StatusResponse)
async def get_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.get("/")
def read_root():
    return {"message": "AudioMix AI Backend is running"}