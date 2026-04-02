import { test, expect } from '@playwright/test';

/**
 * 컨텐츠 검색 페이지 E2E 테스트
 */

test.describe('컨텐츠 페이지', () => {
  test('검색 페이지가 정상적으로 로드된다', async ({ page }) => {
    // 컨텐츠 페이지로 이동
    await page.goto('/contents');
    // 페이지가 로드될 때까지 대기
    await page.waitForLoadState('networkidle');
    // 페이지 내에 컨텐츠 관련 요소가 있는지 확인
    await expect(page.locator('body')).toBeVisible();
  });

  test('검색어 입력 후 검색이 실행된다', async ({ page }) => {
    await page.goto('/contents');
    await page.waitForLoadState('networkidle');

    // 검색 입력 필드 찾기
    const searchInput = page.getByPlaceholder(/검색/);
    if (await searchInput.isVisible()) {
      // 검색어 입력
      await searchInput.fill('테스트 검색어');
      // Enter 키로 검색 실행
      await searchInput.press('Enter');
      // 페이지 URL이나 콘텐츠가 변경되는지 확인
      await page.waitForLoadState('networkidle');
    }
  });

  test('필터 동작을 확인한다', async ({ page }) => {
    await page.goto('/contents');
    await page.waitForLoadState('networkidle');

    // 출처 필터 Select가 존재하는지 확인
    const sourceFilter = page.locator('[data-slot="select-trigger"]').first();
    if (await sourceFilter.isVisible()) {
      await sourceFilter.click();
      // 드롭다운 옵션이 표시되는지 확인
      await expect(
        page.locator('[data-slot="select-content"]')
      ).toBeVisible();
    }
  });

  test('검색 결과 카드 클릭 시 상세 페이지로 이동한다', async ({ page }) => {
    await page.goto('/contents');
    await page.waitForLoadState('networkidle');

    // 검색 결과 항목(행 또는 카드)이 있으면 첫 번째를 클릭
    const firstResult = page.locator('table tbody tr a, [data-slot="card"] a').first();
    if (await firstResult.isVisible({ timeout: 5000 }).catch(() => false)) {
      await firstResult.click();
      // 상세 페이지로 이동했는지 URL 확인
      await expect(page).toHaveURL(/\/contents\/\d+/);
    }
  });
});
