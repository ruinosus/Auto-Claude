import { useMemo, useEffect, useState } from 'react';

/**
 * Hook that reads CSS variable values and returns actual color strings
 * Works with theme switching by re-reading values when theme changes
 */
export function useChartColors() {
  const [colors, setColors] = useState({
    chart1: '#A5A66A',
    chart2: '#4EBE96',
    chart3: '#479FFA',
    chart4: '#D2D714',
    chart5: '#D84F68',
    primary: '#A5A66A',
    destructive: '#DC2626',
    muted: '#71717A',
    card: '#FFFFFF',
    border: '#E4E4E7'
  });

  useEffect(() => {
    const updateColors = () => {
      const root = document.documentElement;
      const computedStyle = getComputedStyle(root);

      const getColor = (varName: string, fallback: string): string => {
        const value = computedStyle.getPropertyValue(varName).trim();
        return value || fallback;
      };

      setColors({
        chart1: getColor('--chart-1', '#A5A66A'),
        chart2: getColor('--chart-2', '#4EBE96'),
        chart3: getColor('--chart-3', '#479FFA'),
        chart4: getColor('--chart-4', '#D2D714'),
        chart5: getColor('--chart-5', '#D84F68'),
        primary: getColor('--primary', '#A5A66A'),
        destructive: getColor('--destructive', '#DC2626'),
        muted: getColor('--muted-foreground', '#71717A'),
        card: getColor('--card', '#FFFFFF'),
        border: getColor('--border', '#E4E4E7')
      });
    };

    // Initial read
    updateColors();

    // Listen for theme changes via mutation observer on html element
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === 'attributes' &&
            (mutation.attributeName === 'class' ||
             mutation.attributeName === 'data-theme' ||
             mutation.attributeName === 'style')) {
          updateColors();
          break;
        }
      }
    });

    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class', 'data-theme', 'style']
    });

    // Also listen for media query changes (system dark mode)
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleMediaChange = () => updateColors();
    mediaQuery.addEventListener('change', handleMediaChange);

    return () => {
      observer.disconnect();
      mediaQuery.removeEventListener('change', handleMediaChange);
    };
  }, []);

  return colors;
}

/**
 * Returns an array of chart colors for use in pie charts, etc.
 */
export function useChartColorArray(): string[] {
  const colors = useChartColors();
  return useMemo(() => [
    colors.chart1,
    colors.chart2,
    colors.chart3,
    colors.chart4,
    colors.chart5
  ], [colors]);
}
