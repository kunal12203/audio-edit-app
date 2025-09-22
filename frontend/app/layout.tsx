import type { Metadata } from 'next';
import { Poppins } from 'next/font/google'; // Import Poppins
import './globals.css';

// Configure the font
const poppins = Poppins({
  subsets: ['latin'],
  weight: ['400', '600', '700'],
});

export const metadata: Metadata = {
  title: 'AI Audio Remixer',
  description: 'Create audio mixes with AI',
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