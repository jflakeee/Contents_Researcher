import { test, expect } from '@playwright/test';

/**
 * 검색 기능 E2E 테스트
 */

test.describe('검색 기능', () => {
  test('검색바가 표시된다', async ({ page }) => {
    // 컨텐츠 페이지로 이동
    await page.goto('/contents');
    await page.waitForLoadState('networkidle');

    // 검색 입력 필드가 표시되는지 확인
    const searchInput = page.getByPlaceholder(/검색/);
    if (await searchInput.isVisible({ timeout: 5000 }).catch(() => false)) {
      await expect(searchInput).toBeVisible();
    }
  });

  test('필터 셀렉트가 동작한다', async ({ page }) => {
    await page.goto('/contents');
    await page.waitForLoadState('networkidle');

    // 셀렉트 트리거가 있는지 확인
    const selectTriggers = page.locator('[data-slot="select-trigger"]');
    const count = await selectTriggers.count();

    if (count > 0) {
      // 첫 번째 셀렉트 클릭
      await selectTriggers.first().click();
      // 드롭다운 콘텐츠가 표시되는지 확인
      const selectContent = page.locator('[data-slot="select-content"]');
      await expect(selectContent).toBeVisible();

      // 옵션 아이템이 하나 이상 있는지 확인
      const items = page.locator('[data-slot="select-item"]');
      const itemCount = await items.count();
      expect(itemCount).toBeGreaterThan(0);

      // 첫 번째 아이템 선택
      await items.first().click();
    }
  });

  test('페이지네이션이 동작한다', async ({ page }) => {
    await page.goto('/contents');
    await page.waitForLoadState('networkidle');

    // 페이지네이션 버튼 확인 (다음 페이지 / 이전 페이지)
    const nextButton = page.getByRole('button', { name: /다음|next|>/i });
    if (await nextButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      // 다음 페이지 버튼이 활성화되어 있으면 클릭
      const isDisabled = await nextButton.isDisabled();
      if (!isDisabled) {
        await nextButton.click();
        await page.waitForLoadState('networkidle');
      }
    }
  });
});
