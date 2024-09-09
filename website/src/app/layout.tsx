import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Head from "next/head";
import { useState } from "react";
import Navbar from "./components/navbar";
const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Grim-Repo",
  description: "Ai version control for all your broken dependencies",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
 

  return (
    <html lang="en">
      <body className={`${inter.className} h-screen bg-white`}>
        <Navbar />
        {children}
      </body>
    </html>
  );
}
