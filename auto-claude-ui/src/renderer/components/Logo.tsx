import { useSettingsStore } from '../stores/settings-store';

interface LogoProps {
  className?: string;
}

export function Logo({ className = '' }: LogoProps) {
  const settings = useSettingsStore((state) => state.settings);
  const colorTheme = settings.colorTheme || 'default';
  const isDark = settings.theme === 'dark' ||
    (settings.theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);

  // Show Avanade logo when Avanade theme is active
  if (colorTheme === 'avanade') {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <img
          src="/images/avanade-logo-brand-wave.png"
          alt="Avanade Logo"
          className="h-8 w-auto"
        />
        <span className="text-base font-semibold tracking-tight">
          Auto Claude
        </span>
      </div>
    );
  }

  // Default text logo for other themes
  return (
    <span className={`text-lg font-bold text-primary ${className}`}>
      Auto Claude
    </span>
  );
}
