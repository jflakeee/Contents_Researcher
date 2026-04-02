"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

/** localStorage 키 */
const STORAGE_KEY = "contents_researcher_settings";

/** 설정값 타입 정의 */
interface Settings {
  // API 키 관리
  youtubeApiKey: string;
  // 수집 주기 (플랫폼별 cron 표현식)
  cronYoutube: string;
  cronAggag: string;
  cronInstagram: string;
  // 분석 설정
  keywordExtractCount: number;
  sentimentThreshold: number;
  // 중요도 가중치
  weightComment: number;
  weightLike: number;
  weightSentimentBias: number;
  weightKeywordRelevance: number;
  weightRecency: number;
}

/** 기본 설정값 */
const DEFAULT_SETTINGS: Settings = {
  youtubeApiKey: "",
  cronYoutube: "0 */6 * * *",
  cronAggag: "0 */6 * * *",
  cronInstagram: "0 */6 * * *",
  keywordExtractCount: 15,
  sentimentThreshold: 0.1,
  weightComment: 0.25,
  weightLike: 0.2,
  weightSentimentBias: 0.15,
  weightKeywordRelevance: 0.25,
  weightRecency: 0.15,
};

/**
 * localStorage에서 설정값 로드
 * - 저장된 값이 없으면 기본값 반환
 */
function loadSettings(): Settings {
  if (typeof window === "undefined") return DEFAULT_SETTINGS;
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) };
    }
  } catch {
    // 파싱 실패 시 기본값 반환
  }
  return DEFAULT_SETTINGS;
}

/**
 * localStorage에 설정값 저장
 */
function saveSettings(settings: Settings): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}

/**
 * 설정 페이지
 * - API 키 관리
 * - 수집 주기 설정 (플랫폼별 cron)
 * - 분석 설정 (키워드 추출 개수, 감성 임계값)
 * - 중요도 가중치 설정
 * - 모든 설정은 localStorage에 저장
 */
export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  // API 키 마스킹 표시 여부
  const [showApiKey, setShowApiKey] = useState(false);
  // 저장 완료 피드백
  const [saved, setSaved] = useState(false);

  // 컴포넌트 마운트 시 localStorage에서 설정 로드
  useEffect(() => {
    setSettings(loadSettings());
  }, []);

  /**
   * 설정값 변경 핸들러
   * - 문자열/숫자 필드 구분하여 처리
   */
  const handleChange = (field: keyof Settings, value: string | number) => {
    setSettings((prev) => ({ ...prev, [field]: value }));
    // 저장 피드백 초기화
    setSaved(false);
  };

  /** 숫자 입력 변경 핸들러 */
  const handleNumberChange = (field: keyof Settings, value: string) => {
    const parsed = parseFloat(value);
    if (!isNaN(parsed)) {
      handleChange(field, parsed);
    }
  };

  /** 설정 저장 핸들러 */
  const handleSave = () => {
    saveSettings(settings);
    setSaved(true);
    // 3초 후 피드백 메시지 숨기기
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">설정</h1>

      {/* API 키 관리 */}
      <Card>
        <CardHeader>
          <CardTitle>API 키 관리</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">YouTube API Key</label>
            <div className="flex gap-2">
              <Input
                type={showApiKey ? "text" : "password"}
                placeholder="YouTube Data API 키를 입력하세요"
                value={settings.youtubeApiKey}
                onChange={(e) => handleChange("youtubeApiKey", e.target.value)}
              />
              <Button
                variant="outline"
                onClick={() => setShowApiKey((prev) => !prev)}
              >
                {showApiKey ? "숨기기" : "표시"}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 수집 주기 설정 */}
      <Card>
        <CardHeader>
          <CardTitle>수집 주기 설정</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* 유튜브 cron */}
          <div className="space-y-2">
            <label className="text-sm font-medium">유튜브 수집 주기 (Cron)</label>
            <Input
              placeholder="예: 0 */6 * * *"
              value={settings.cronYoutube}
              onChange={(e) => handleChange("cronYoutube", e.target.value)}
            />
          </div>
          {/* 아깍 cron */}
          <div className="space-y-2">
            <label className="text-sm font-medium">아깍 수집 주기 (Cron)</label>
            <Input
              placeholder="예: 0 */6 * * *"
              value={settings.cronAggag}
              onChange={(e) => handleChange("cronAggag", e.target.value)}
            />
          </div>
          {/* 인스타그램 cron */}
          <div className="space-y-2">
            <label className="text-sm font-medium">인스타그램 수집 주기 (Cron)</label>
            <Input
              placeholder="예: 0 */6 * * *"
              value={settings.cronInstagram}
              onChange={(e) => handleChange("cronInstagram", e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      {/* 분석 설정 */}
      <Card>
        <CardHeader>
          <CardTitle>분석 설정</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* 키워드 추출 개수 */}
          <div className="space-y-2">
            <label className="text-sm font-medium">키워드 추출 개수</label>
            <Input
              type="number"
              min={1}
              max={100}
              value={settings.keywordExtractCount}
              onChange={(e) =>
                handleNumberChange("keywordExtractCount", e.target.value)
              }
            />
            <p className="text-xs text-muted-foreground">
              컨텐츠에서 추출할 키워드 최대 개수 (기본: 15)
            </p>
          </div>
          {/* 감성 임계값 */}
          <div className="space-y-2">
            <label className="text-sm font-medium">감성 임계값</label>
            <Input
              type="number"
              step={0.01}
              min={0}
              max={1}
              value={settings.sentimentThreshold}
              onChange={(e) =>
                handleNumberChange("sentimentThreshold", e.target.value)
              }
            />
            <p className="text-xs text-muted-foreground">
              감성 분류 기준값. 이 값 이상이면 긍정, 음수면 부정 (기본: 0.1)
            </p>
          </div>
        </CardContent>
      </Card>

      {/* 중요도 가중치 설정 */}
      <Card>
        <CardHeader>
          <CardTitle>중요도 가중치 설정</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* 댓글수 가중치 */}
          <div className="space-y-2">
            <label className="text-sm font-medium">댓글수 가중치</label>
            <Input
              type="number"
              step={0.01}
              min={0}
              max={1}
              value={settings.weightComment}
              onChange={(e) =>
                handleNumberChange("weightComment", e.target.value)
              }
            />
          </div>
          {/* 좋아요수 가중치 */}
          <div className="space-y-2">
            <label className="text-sm font-medium">좋아요수 가중치</label>
            <Input
              type="number"
              step={0.01}
              min={0}
              max={1}
              value={settings.weightLike}
              onChange={(e) => handleNumberChange("weightLike", e.target.value)}
            />
          </div>
          {/* 감성편향도 가중치 */}
          <div className="space-y-2">
            <label className="text-sm font-medium">감성편향도 가중치</label>
            <Input
              type="number"
              step={0.01}
              min={0}
              max={1}
              value={settings.weightSentimentBias}
              onChange={(e) =>
                handleNumberChange("weightSentimentBias", e.target.value)
              }
            />
          </div>
          {/* 키워드관련성 가중치 */}
          <div className="space-y-2">
            <label className="text-sm font-medium">키워드관련성 가중치</label>
            <Input
              type="number"
              step={0.01}
              min={0}
              max={1}
              value={settings.weightKeywordRelevance}
              onChange={(e) =>
                handleNumberChange("weightKeywordRelevance", e.target.value)
              }
            />
          </div>
          {/* 최신성 가중치 */}
          <div className="space-y-2">
            <label className="text-sm font-medium">최신성 가중치</label>
            <Input
              type="number"
              step={0.01}
              min={0}
              max={1}
              value={settings.weightRecency}
              onChange={(e) =>
                handleNumberChange("weightRecency", e.target.value)
              }
            />
          </div>
          <p className="text-xs text-muted-foreground">
            모든 가중치의 합은 1.0이 되어야 합니다. 현재 합계:{" "}
            <span className="font-mono font-medium">
              {(
                settings.weightComment +
                settings.weightLike +
                settings.weightSentimentBias +
                settings.weightKeywordRelevance +
                settings.weightRecency
              ).toFixed(2)}
            </span>
          </p>
        </CardContent>
      </Card>

      {/* 저장 버튼 */}
      <div className="flex items-center gap-4">
        <Button onClick={handleSave}>설정 저장</Button>
        {saved && (
          <span className="text-sm text-green-600">설정이 저장되었습니다.</span>
        )}
      </div>
    </div>
  );
}
