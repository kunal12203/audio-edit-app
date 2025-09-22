'use client';

import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import { Music, Wand2, Download, CheckCircle2, LoaderCircle, PenLine, Cloud, Combine } from 'lucide-react';

const statusSteps = [
  { key: 'parsing_prompt', title: 'Analyzing Prompt', icon: <PenLine /> },
  { key: 'searching_youtube', title: 'Searching Sources', icon: <Cloud /> },
  { key: 'downloading_audio', title: 'Downloading Audio', icon: <Download /> },
  { key: 'processing_audio', title: 'Mixing & Mastering', icon: <Combine /> },
];

export default function HomePage() {
  const [prompt, setPrompt] = useState<string>('');
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>('idle');
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const studioRef = useRef<HTMLDivElement>(null);

  // This useEffect hook now contains the polling logic with the required header
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (jobId && isLoading) {
      interval = setInterval(async () => {
        try {
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
          // FINAL FIX: Add the ngrok header to the status check fetch call
          const response = await fetch(`${apiUrl}/status/${jobId}`, {
            headers: {
              'ngrok-skip-browser-warning': 'true'
            }
          });
          if (!response.ok) throw new Error('Status check failed');
          const data = await response.json();
          setStatus(data.status);
          if (data.status === 'complete' || data.status === 'failed') {
            setIsLoading(false);
            if (data.file_url) setFileUrl(data.file_url);
            clearInterval(interval);
          }
        } catch (error) {
          setStatus('failed');
          setIsLoading(false);
          clearInterval(interval);
        }
      }, 3000);
    }
    return () => clearInterval(interval);
  }, [jobId, isLoading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || isLoading) return;
    setIsLoading(true);
    setStatus('parsing_prompt');
    setFileUrl(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const response = await fetch(`${apiUrl}/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true' // This one was already fixed
        },
        body: JSON.stringify({ prompt }),
      });
      if (!response.ok) throw new Error('Failed to start job');
      const data = await response.json();
      setJobId(data.job_id);
    } catch (error) {
      setStatus('failed');
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-slate-50 text-slate-800 font-sans">
      <Header />
      <Hero onCTAClick={() => studioRef.current?.scrollIntoView()} />
      <HowItWorks />
      
      <main id="studio" ref={studioRef} className="py-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.5 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl sm:text-5xl font-bold tracking-tight text-slate-900">
              Creation <span className="text-indigo-600">Studio</span>
            </h2>
            <p className="mt-4 text-lg text-slate-600">
              Bring your audio ideas to life. Be as descriptive as you like.
            </p>
          </motion.div>
          
          <form onSubmit={handleSubmit} className="p-8 bg-white rounded-2xl shadow-xl border border-slate-200">
            <div className="mb-6">
              <label htmlFor="prompt" className="text-lg font-semibold mb-3 block text-slate-700">Your Audio Vision</label>
              <div className="relative">
                <textarea
                  id="prompt"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  className="w-full h-48 p-4 rounded-lg bg-slate-100 border-2 border-slate-200 focus:ring-4 focus:ring-indigo-300 focus:border-indigo-500 focus:outline-none transition-all duration-300"
                  placeholder="e.g., Mix the synth riff from 'Take On Me' (0:10-0:25) with the drum beat from Queen's 'We Will Rock You' (0:00-0:15)..."
                />
              </div>
            </div>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-3 py-4 px-6 rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-bold text-lg shadow-lg hover:shadow-xl transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <><LoaderCircle className="w-6 h-6 animate-spin" /> Orchestrating...</>
              ) : (
                <><Wand2 className="w-6 h-6" /> Generate My Mix</>
              )}
            </motion.button>
          </form>
          
          {isLoading && <StatusDisplay currentStatus={status} />}
          {fileUrl && !isLoading && <ResultDisplay fileUrl={fileUrl} />}
        </div>
      </main>
      <Footer />
    </div>
  );
}

// --- SUB-COMPONENTS ---

const Header = () => (
  <header className="fixed top-0 left-0 w-full p-4 bg-white backdrop-blur-lg border-b border-slate-200 z-50">
    <div className="max-w-7xl mx-auto flex justify-between items-center">
      <a href="#" className="flex items-center gap-2">
        <Music className="text-indigo-600" />
        <span className="font-bold text-xl text-slate-900">AudioMix AI</span>
      </a>
      <a href="#studio" className="px-4 py-2 bg-indigo-600 text-white rounded-lg font-semibold hover:bg-indigo-700 transition-colors shadow-sm hover:shadow-md">
        Create Now
      </a>
    </div>
  </header>
);

const Hero = ({ onCTAClick }: { onCTAClick: () => void }) => (
  <section className="pt-40 pb-24 text-center bg-white">
    <div className="max-w-4xl mx-auto px-4">
      <motion.h1 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className="text-5xl sm:text-6xl md:text-7xl font-extrabold tracking-tighter text-slate-900"
      >
        The Future of Audio <br/> is in Your <span className="bg-clip-text text-transparent bg-gradient-to-r from-indigo-500 to-purple-500">Words</span>.
      </motion.h1>
      <motion.p 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="mt-6 text-lg sm:text-xl text-slate-600 max-w-2xl mx-auto"
      >
        Describe any audio mashup, remix, or soundscape. Our AI-powered engine will compose it for you in seconds.
      </motion.p>
      <motion.button 
        onClick={onCTAClick}
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.3, type: 'spring', stiffness: 100 }}
        className="mt-12 px-8 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-bold text-lg rounded-full shadow-lg hover:shadow-xl transform hover:-translate-y-1 transition-all duration-300"
      >
        Start Creating for Free
      </motion.button>
    </div>
  </section>
);

const HowItWorks = () => (
  <section className="py-24 bg-slate-50 border-y border-slate-200">
    <div className="max-w-6xl mx-auto px-4 text-center">
      <h2 className="text-4xl font-bold text-slate-900 mb-4">How It Works</h2>
      <p className="text-lg text-slate-600 mb-16">In three simple steps.</p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-left">
        {[
          { icon: <PenLine size={28} />, title: '1. Describe', text: 'Write a detailed prompt describing the clips and sequence you envision.' },
          { icon: <Wand2 size={28} />, title: '2. AI Mixes', text: 'Our AI engine finds the audio, trims the clips, and masters the final mix.' },
          { icon: <Download size={28} />, title: '3. Download', text: 'Receive a high-quality MP3 of your creation, ready to share.' },
        ].map((step, i) => (
          <motion.div
            key={step.title}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.5 }}
            transition={{ duration: 0.5, delay: i * 0.1 }}
            className="p-8 bg-white rounded-xl shadow-lg hover:shadow-xl hover:-translate-y-2 transition-all duration-300"
          >
            <div className="w-16 h-16 flex items-center justify-center bg-indigo-100 text-indigo-600 rounded-full mb-6">
              {step.icon}
            </div>
            <h3 className="text-2xl font-bold text-slate-900 mb-2">{step.title}</h3>
            <p className="text-slate-600">{step.text}</p>
          </motion.div>
        ))}
      </div>
    </div>
  </section>
);

const StatusDisplay = ({ currentStatus }: { currentStatus: string }) => {
  const currentStepIndex = statusSteps.findIndex(s => s.key === currentStatus);
  return (
    <div className="mt-12 p-6 bg-white rounded-xl shadow-lg border border-slate-200">
      <h3 className="text-xl font-bold text-center mb-6">Your Mix is in Production...</h3>
      <div className="flex flex-col md:flex-row justify-between gap-4">
        {statusSteps.map((step, index) => {
          const isCompleted = currentStepIndex > index;
          const isInProgress = currentStepIndex === index;
          return (
            <div key={step.key} className="flex items-center gap-3 p-3 w-full justify-center md:flex-col md:text-center">
              <div className={clsx('w-12 h-12 flex items-center justify-center rounded-full border-2 transition-all duration-300 flex-shrink-0', {
                'bg-green-500 border-green-500 text-white': isCompleted,
                'bg-indigo-600 border-indigo-600 text-white animate-pulse': isInProgress,
                'bg-slate-100 border-slate-300 text-slate-400': !isCompleted && !isInProgress,
              })}>
                {isCompleted ? <CheckCircle2 /> : (isInProgress ? <LoaderCircle className="animate-spin"/> : step.icon)}
              </div>
              <h4 className={clsx('font-semibold transition-colors', { 'text-slate-900': isCompleted || isInProgress, 'text-slate-500': !isCompleted && !isInProgress })}>{step.title}</h4>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const ResultDisplay = ({ fileUrl }: { fileUrl: string }) => (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mt-12 p-8 text-center bg-green-50 border-2 border-green-200 rounded-2xl">
        <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-4" />
        <h3 className="text-3xl font-bold text-green-800">Your Masterpiece is Ready!</h3>
        <p className="mt-2 text-green-700">The AI has finished composing your audio mix.</p>
        <a href={`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}${fileUrl}`} download className="mt-6 inline-flex items-center gap-3 py-3 px-8 rounded-full bg-green-600 text-white font-bold text-lg shadow-lg hover:bg-green-700 transform hover:-translate-y-0.5 transition-all duration-300">
            <Download /> Download MP3
        </a>
    </motion.div>
);

const Footer = () => (
    <footer className="py-8 bg-slate-100 border-t border-slate-200">
        <div className="max-w-7xl mx-auto px-4 text-center text-slate-500">
            <p>&copy; {new Date().getFullYear()} AudioMix AI. The future of sound is here.</p>
        </div>
    </footer>
);