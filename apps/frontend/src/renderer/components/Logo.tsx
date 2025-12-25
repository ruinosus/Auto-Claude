import { useSettingsStore } from '../stores/settings-store';
import avanadeLogoBrandWave from '../../../public/images/avanade-logo-brand-wave.png';
import intraaiLogo from '../../../public/images/intraai-logo.svg';

interface LogoProps {
  className?: string;
}

export function Logo({ className = '' }: LogoProps) {
  const settings = useSettingsStore((state) => state.settings);
  const colorTheme = settings.colorTheme || 'default';

  // Show Avanade logo when Avanade theme is active (logo only, no text)
  if (colorTheme === 'avanade') {
    return (
      <div className={`flex items-center ${className}`}>
        <img
          src={avanadeLogoBrandWave}
          alt="Avanade Logo"
          className="h-8 w-auto"
        />
      </div>
    );
  }

  // Show IntraAI logo when IntraAI theme is active (logo only, no text)
  if (colorTheme === 'intraai') {
    return (
      <div className={`flex items-center ${className}`}>
        <img
          src={intraaiLogo}
          alt="IntraAI Logo"
          className="h-8 w-auto"
        />
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
