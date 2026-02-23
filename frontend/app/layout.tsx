import type { Metadata } from "next";
import { Outfit, Source_Sans_3 } from "next/font/google";
import "./globals.css";

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
  display: "swap",
});

const sourceSans = Source_Sans_3({
  subsets: ["latin"],
  variable: "--font-source-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "SaiV - AI Learning Assistant",
  description:
    "Transform YouTube videos and PDFs into flashcards, quizzes, and chat with an AI tutor powered by RAG.",
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${outfit.variable} ${sourceSans.variable}`}>
      <body className="font-body antialiased">
        <div className="gradient-orb gradient-orb-1" aria-hidden />
        <div className="gradient-orb gradient-orb-2" aria-hidden />
        <div className="relative z-10">{children}</div>
      </body>
    </html>
  );
}
