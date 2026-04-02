import { test, expect } from '@playwright/test';

/**
 * 대시보드 페이지 E2E 테스트
 */

test.describe('대시보드 페이지', () => {
  test('대시보드 페이지가 정상적으로 로드된다', async ({ page }) => {
    // 대시보드 페이지로 이동
    await page.goto('/dashboard');
    // 페이지 제목 확인
    await expect(page.getByRole('heading', { name: '대시보드' })).toBeVisible();
  });

  test('출처별 수집 현황 카드가 표시된다', async ({ page }) => {
    await page.goto('/dashboard');
    // 수집 현황 섹션 제목 확인
    await expect(
      page.getByRole('heading', { name: '출처별 수집 현황' })
    ).toBeVisible();
  });

  test('네비게이션 메뉴가 정상적으로 동작한다', async ({ page }) => {
    await page.goto('/dashboard');

    // 사이드바 메뉴 항목들 확인
    await expect(page.getByRole('link', { name: /대시보드/ })).toBeVisible();
    await expect(page.getByRole('link', { name: /컨텐츠/ })).toBeVisible();
    await expect(page.getByRole('link', { name: /키워드/ })).toBeVisible();
    await expect(page.getByRole('link', { name: /스케줄러/ })).toBeVisible();
    await expect(page.getByRole('link', { name: /설정/ })).toBeVisible();

    // 키워드 페이지로 이동
    await page.getByRole('link', { name: /키워드/ }).click();
    await expect(page).toHaveURL(/\/keywords/);
    await expect(
      page.getByRole('heading', { name: '키워드 트렌드' })
    ).toBeVisible();

    // 스케줄러 페이지로 이동
    await page.getByRole('link', { name: /스케줄러/ }).click();
    await expect(page).toHaveURL(/\/scheduler/);
    await expect(
      page.getByRole('heading', { name: '스케줄러' })
    ).toBeVisible();

    // 설정 페이지로 이동
    await page.getByRole('link', { name: /설정/ }).click();
    await expect(page).toHaveURL(/\/settings/);
    await expect(page.getByRole('heading', { name: '설정' })).toBeVisible();
  });
});
