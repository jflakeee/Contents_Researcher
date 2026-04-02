import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { format, parseISO } from "date-fns";
import { ko } from "date-fns/locale";

/** Tailwind 클래스 병합 유틸 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** 날짜 문자열을 한국어 형식으로 변환 */
export function formatDate(dateString: string): string {
  try {
    const date = parseISO(dateString);
    return format(date, "yyyy년 MM월 dd일 HH:mm", { locale: ko });
  } catch {
    return dateString;
  }
}

/** 숫자를 축약 형식으로 변환 (1.2K, 3.4M 등) */
export function formatNumber(num: number): string {
  if (num >= 1_000_000) {
    return `${(num / 1_000_000).toFixed(1)}M`;
  }
  if (num >= 1_000) {
    return `${(num / 1_000).toFixed(1)}K`;
  }
  return num.toString();
}

/** 감성 분석 결과에 따른 Tailwind 색상 클래스 반환 */
export function getSentimentColor(sentiment: string): string {
  switch (sentiment) {
    case "positive":
      return "bg-green-100 text-green-800";
    case "negative":
      return "bg-red-100 text-red-800";
    case "neutral":
      return "bg-gray-100 text-gray-800";
    default:
      return "bg-gray-100 text-gray-500";
  }
}

/** 감성 분석 결과를 한국어 라벨로 변환 */
export function getSentimentLabel(sentiment: string): string {
  switch (sentiment) {
    case "positive":
      return "긍정";
    case "negative":
      return "부정";
    case "neutral":
      return "중립";
    default:
      return "미분석";
  }
}

/** 출처명에 따른 텍스트 아이콘 반환 */
export function getSourceIcon(source: string): string {
  switch (source.toLowerCase()) {
    case "youtube":
      return "[YT]";
    case "reddit":
      return "[RD]";
    case "twitter":
    case "x":
      return "[TW]";
    case "naver":
      return "[NV]";
    case "daum":
      return "[DM]";
    case "google":
      return "[GG]";
    default:
      return "[--]";
  }
}
