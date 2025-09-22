import type { Metadata } from 'next';
import { Poppins } from 'next/font/google';
import './globals.css';

// Configure the Poppins font
const poppins = Poppins({
  subsets: ['latin'],
  weight: ['400', '600', '700', '800'],
});

export const metadata: Metadata = {
  title: 'AudioMix AI',
  description: 'The future of audio is in your words.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={poppins.className}>{children}</body>
    </html>
  );
}