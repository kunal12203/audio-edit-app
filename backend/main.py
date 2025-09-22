import os
import json
import uuid
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
from yt_dlp import YoutubeDL
from pydub import AudioSegment

# Load environment variables from .env file
load_dotenv()

# --- Helper Functions (All included here) ---

def convert_time_to_ms(time_str: str):
    """Converts MM:SS or M:SS string to milliseconds."""
    parts = time_str.split(':')
    minutes = int(parts[0])
    seconds = int(parts[1])
    return (minutes * 60 + seconds) * 1000

def search_youtube_for_url(song_name: str):
    """Searches YouTube for a song and returns the URL of the first result."""
    try:
        print(f"🔍 Searching YouTube for '{song_name}'...")
        ydl_opts = {
            'format': 'bestaudio/best',
            'default_search': 'ytsearch1',
            'quiet': True,
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{song_name}", download=False)
            if 'entries' in info and len(info['entries']) > 0:
                video_url = info['entries'][0]['webpage_url']
                print(f"🔗 Found video URL: {video_url}")
                return video_url
    except Exception as e:
        print(f"❌ An error occurred during YouTube search: {e}")
        return None

def download_audio_from_youtube(url: str, output_path="."):
    """Downloads a YouTube video as an MP3 audio file."""
    try:
        output_template = os.path.join(output_path, '%(title)s.%(ext)s')
        ydl_opts = {
            'format': 'bestaudio/best', 'outtmpl': output_template,
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            'noplaylist': True,
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            base, _ = os.path.splitext(filename)
            mp3_filepath = base + '.mp3'
            if os.path.exists(mp3_filepath):
                print(f"✅ Successfully downloaded and converted to: {mp3_filepath}")
                return mp3_filepath
    except Exception as e:
        print(f"❌ An error occurred during download: {e}")
        return None

def parse_prompt_with_openai(prompt: str):
    """Sends a prompt to OpenAI and expects a structured JSON output for multiple songs."""
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
    print("🤖 Sending prompt to OpenAI for processing...")
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    response_content = response.choices[0].message.content
    print("✅ OpenAI responded successfully.")
    return json.loads(response_content)

# --- App Setup ---
app = FastAPI()
jobs = {} # In-memory "database" to track job status

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3003"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if not os.path.exists("output"):
    os.makedirs("output")

app.mount("/output", StaticFiles(directory="output"), name="output")

# --- API Models ---
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
    try:
        jobs[job_id]["status"] = "🤖 Analyzing your prompt..."
        parsed_data = parse_prompt_with_openai(prompt)
        if not parsed_data or "clips" not in parsed_data:
            raise ValueError("Failed to parse prompt with OpenAI.")

        processed_clips = {}
        downloaded_songs = {}

        for i, clip_info in enumerate(parsed_data["clips"]):
            song_name = clip_info["song_name"]
            clip_name = clip_info["name"]
            jobs[job_id]["status"] = f"🎵 Processing clip {i+1}/{len(parsed_data['clips'])}: '{song_name}'"

            if song_name in downloaded_songs:
                audio_file_path = downloaded_songs[song_name]
            else:
                song_url = search_youtube_for_url(song_name)
                if not song_url: raise ValueError(f"Could not find '{song_name}'")
                
                audio_file_path = download_audio_from_youtube(song_url, output_path="output")
                if not audio_file_path: raise ValueError(f"Failed to download '{song_name}'")
                
                downloaded_songs[song_name] = audio_file_path
                downloaded_files.append(audio_file_path)

            sound = AudioSegment.from_mp3(audio_file_path)
            start_ms = convert_time_to_ms(clip_info['start'])
            end_ms = convert_time_to_ms(clip_info['end'])
            trimmed_clip = sound[start_ms:end_ms]
            processed_clips[clip_name] = trimmed_clip

        jobs[job_id]["status"] = "🔗 Merging all clips..."
        final_audio = AudioSegment.silent(duration=0)
        for clip_name in parsed_data["sequence"]:
            if clip_name in processed_clips:
                final_audio += processed_clips[clip_name]
        
        output_filename = f"output/{job_id}.mp3"
        final_audio.export(output_filename, format="mp3")

        jobs[job_id]["status"] = "complete"
        jobs[job_id]["file_url"] = f"/{output_filename}"

    except Exception as e:
        print(f"Error in job {job_id}: {e}")
        jobs[job_id]["status"] = "failed"
    finally:
        print("Cleaning up source files...")
        for file_path in downloaded_files:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError as e:
                    print(f"Error deleting file {file_path}: {e}")

# --- API Endpoints ---
@app.post("/generate", response_model=JobResponse)
async def generate_audio(request: PromptRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "pending", "file_url": None}
    background_tasks.add_task(run_multi_song_processing, request.prompt, job_id)
    return {"job_id": job_id}

@app.get("/status/{job_id}", response_model=StatusResponse)
async def get_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job