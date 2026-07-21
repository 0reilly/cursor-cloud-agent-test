import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Apple Notes Clone",
  description: "A modern Apple Notes clone built with Next.js and Tailwind CSS",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
