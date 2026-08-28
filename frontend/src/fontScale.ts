export type FontScale = "default" | "large" | "xlarge";

export const FONT_SCALE_STORAGE_KEY = "salesbooster.font-scale";

const fontScales: ReadonlySet<string> = new Set(["default", "large", "xlarge"]);

export function readFontScale(storage?: Pick<Storage, "getItem">): FontScale {
  const value = storage?.getItem(FONT_SCALE_STORAGE_KEY);
  return value && fontScales.has(value) ? value as FontScale : "default";
}

export function saveFontScale(scale: FontScale, storage?: Pick<Storage, "setItem">): void {
  storage?.setItem(FONT_SCALE_STORAGE_KEY, scale);
}

export function applyFontScale(
  scale: FontScale,
  root?: Pick<HTMLElement, "dataset">,
): void {
  if (root) {
    root.dataset.fontScale = scale;
    return;
  }
  if (typeof document !== "undefined") {
    document.documentElement.dataset.fontScale = scale;
  }
}
