import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KW-LIFE — 광운대 맞춤 공고 보드",
  description: "광운대학교 학생 맞춤형 비교과 활동 추천 시스템",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
