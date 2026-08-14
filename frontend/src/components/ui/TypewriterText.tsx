'use client';
import { useState, useEffect } from 'react';

interface TypewriterTextProps {
  text: string;
  speed?: number; // ms per character
  delay?: number; // initial delay ms
  className?: string;
}

export function TypewriterText({ text, speed = 10, delay = 250, className = '' }: TypewriterTextProps) {
  const [displayedText, setDisplayedText] = useState('');
  const [isDone, setIsDone] = useState(false);

  useEffect(() => {
    setDisplayedText('');
    setIsDone(false);

    let currentIndex = 0;
    const timeout = setTimeout(() => {
      const interval = setInterval(() => {
        if (currentIndex < text.length) {
          // Increment in chunks of 2-3 characters for ultra-smooth fast typing feel
          const step = Math.min(3, text.length - currentIndex);
          currentIndex += step;
          setDisplayedText(text.slice(0, currentIndex));
        } else {
          setIsDone(true);
          clearInterval(interval);
        }
      }, speed);

      return () => clearInterval(interval);
    }, delay);

    return () => clearTimeout(timeout);
  }, [text, speed, delay]);

  return (
    <span className={className}>
      {displayedText}
      {!isDone && (
        <span className="inline-block w-1.5 h-3.5 ml-0.5 bg-indigo-600 animate-pulse rounded-sm align-middle" />
      )}
    </span>
  );
}
