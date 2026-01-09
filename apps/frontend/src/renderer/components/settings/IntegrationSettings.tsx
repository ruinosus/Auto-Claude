import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Key,
  Eye,
  EyeOff,
  Info,
  Users,
  Plus,
  Trash2,
  Star,
  Check,
  Pencil,
  X,
  Loader2,
  LogIn,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  Activity,
  AlertCircle,
  Cloud,
  Server
} from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Switch } from '../ui/switch';
import { cn } from '../../lib/utils';
import { Tooltip, TooltipContent, TooltipTrigger } from '../ui/tooltip';
import { SettingsSection } from './SettingsSection';
import { loadClaudeProfiles as loadGlobalClaudeProfiles } from '../../stores/claude-profile-store';
import { useClaudeLoginTerminal } from '../../hooks/useClaudeLoginTerminal';
import type { AppSettings, ClaudeProfile, ClaudeAutoSwitchSettings } from '../../../shared/types';

interface IntegrationSettingsProps {
  settings: AppSettings;
  onSettingsChange: (settings: AppSettings) => void;
  isOpen: boolean;
}

/**
 * Integration settings for Claude accounts and API keys
 */
export function IntegrationSettings({ settings, onSettingsChange, isOpen }: IntegrationSettingsProps) {
  const { t } = useTranslation('settings');
  const { t: tCommon } = useTranslation('common');
  // Password visibility toggle for global API keys
  const [showGlobalOpenAIKey, setShowGlobalOpenAIKey] = useState(false);
  const [showGlobalAzureApiKey, setShowGlobalAzureApiKey] = useState(false);
  const [globalAzureUrlError, setGlobalAzureUrlError] = useState<string | null>(null);

  // Claude Accounts state
  const [claudeProfiles, setClaudeProfiles] = useState<ClaudeProfile[]>([]);
  const [activeProfileId, setActiveProfileId] = useState<string | null>(null);
  const [isLoadingProfiles, setIsLoadingProfiles] = useState(false);
  const [newProfileName, setNewProfileName] = useState('');
  const [isAddingProfile, setIsAddingProfile] = useState(false);
  const [deletingProfileId, setDeletingProfileId] = useState<string | null>(null);
  const [editingProfileId, setEditingProfileId] = useState<string | null>(null);
  const [editingProfileName, setEditingProfileName] = useState('');
  const [authenticatingProfileId, setAuthenticatingProfileId] = useState<string | null>(null);
  const [expandedTokenProfileId, setExpandedTokenProfileId] = useState<string | null>(null);
  const [manualToken, setManualToken] = useState('');
  const [manualTokenEmail, setManualTokenEmail] = useState('');
  const [showManualToken, setShowManualToken] = useState(false);
  const [savingTokenProfileId, setSavingTokenProfileId] = useState<string | null>(null);

  // Azure Foundry profile creation state
  const [isAddingAzureProfile, setIsAddingAzureProfile] = useState(false);
  const [newAzureProfileName, setNewAzureProfileName] = useState('');
  const [newAzureApiKey, setNewAzureApiKey] = useState('');
  const [newAzureBaseUrl, setNewAzureBaseUrl] = useState('');
  const [showNewAzureApiKey, setShowNewAzureApiKey] = useState(false);
  const [azureUrlError, setAzureUrlError] = useState<string | null>(null);
  const [isSavingAzureProfile, setIsSavingAzureProfile] = useState(false);

  // Auto-swap settings state
  const [autoSwitchSettings, setAutoSwitchSettings] = useState<ClaudeAutoSwitchSettings | null>(null);
  const [isLoadingAutoSwitch, setIsLoadingAutoSwitch] = useState(false);

  // Load Claude profiles and auto-swap settings when section is shown
  useEffect(() => {
    if (isOpen) {
      loadClaudeProfiles();
      loadAutoSwitchSettings();
    }
  }, [isOpen]);

  // Listen for login terminal creation - makes the terminal visible so user can see OAuth flow
  useClaudeLoginTerminal();

  // Listen for OAuth authentication completion
  useEffect(() => {
    const unsubscribe = window.electronAPI.onTerminalOAuthToken(async (info) => {
      if (info.success && info.profileId) {
        // Reload profiles to show updated state
        await loadClaudeProfiles();
        // Show simple success notification
        alert(`✅ Profile authenticated successfully!\n\n${info.email ? `Account: ${info.email}` : 'Authentication complete.'}\n\nYou can now use this profile.`);
      }
    });

    return unsubscribe;
  }, []);

  const loadClaudeProfiles = async () => {
    setIsLoadingProfiles(true);
    try {
      const result = await window.electronAPI.getClaudeProfiles();
      if (result.success && result.data) {
        setClaudeProfiles(result.data.profiles);
        setActiveProfileId(result.data.activeProfileId);
        // Also update the global store
        await loadGlobalClaudeProfiles();
      }
    } catch (err) {
      console.error('Failed to load Claude profiles:', err);
    } finally {
      setIsLoadingProfiles(false);
    }
  };

  const handleAddProfile = async () => {
    if (!newProfileName.trim()) return;

    setIsAddingProfile(true);
    try {
      const profileName = newProfileName.trim();
      const profileSlug = profileName.toLowerCase().replace(/\s+/g, '-');

      const result = await window.electronAPI.saveClaudeProfile({
        id: `profile-${Date.now()}`,
        name: profileName,
        configDir: `~/.claude-profiles/${profileSlug}`,
        isDefault: false,
        createdAt: new Date()
      });

      if (result.success && result.data) {
        // Initialize the profile
        const initResult = await window.electronAPI.initializeClaudeProfile(result.data.id);

        if (initResult.success) {
          await loadClaudeProfiles();
          setNewProfileName('');
          // Note: The terminal is now visible in the UI via the onTerminalAuthCreated event
          // Users can see the 'claude setup-token' output directly
        } else {
          await loadClaudeProfiles();
          alert(`Failed to start authentication: ${initResult.error || 'Please try again.'}`);
        }
      }
    } catch (err) {
      console.error('Failed to add profile:', err);
      alert('Failed to add profile. Please try again.');
    } finally {
      setIsAddingProfile(false);
    }
  };

  const handleDeleteProfile = async (profileId: string) => {
    setDeletingProfileId(profileId);
    try {
      const result = await window.electronAPI.deleteClaudeProfile(profileId);
      if (result.success) {
        await loadClaudeProfiles();
      }
    } catch (err) {
      console.error('Failed to delete profile:', err);
    } finally {
      setDeletingProfileId(null);
    }
  };

  const startEditingProfile = (profile: ClaudeProfile) => {
    setEditingProfileId(profile.id);
    setEditingProfileName(profile.name);
  };

  const cancelEditingProfile = () => {
    setEditingProfileId(null);
    setEditingProfileName('');
  };

  const handleRenameProfile = async () => {
    if (!editingProfileId || !editingProfileName.trim()) return;

    try {
      const result = await window.electronAPI.renameClaudeProfile(editingProfileId, editingProfileName.trim());
      if (result.success) {
        await loadClaudeProfiles();
      }
    } catch (err) {
      console.error('Failed to rename profile:', err);
    } finally {
      setEditingProfileId(null);
      setEditingProfileName('');
    }
  };

  const handleSetActiveProfile = async (profileId: string) => {
    try {
      const result = await window.electronAPI.setActiveClaudeProfile(profileId);
      if (result.success) {
        setActiveProfileId(profileId);
        await loadGlobalClaudeProfiles();
      }
    } catch (err) {
      console.error('Failed to set active profile:', err);
    }
  };

  const handleAuthenticateProfile = async (profileId: string) => {
    setAuthenticatingProfileId(profileId);
    try {
      const initResult = await window.electronAPI.initializeClaudeProfile(profileId);
      if (!initResult.success) {
        alert(`Failed to start authentication: ${initResult.error || 'Please try again.'}`);
      }
      // Note: If successful, the terminal is now visible in the UI via the onTerminalAuthCreated event
      // Users can see the 'claude setup-token' output and complete OAuth flow directly
    } catch (err) {
      console.error('Failed to authenticate profile:', err);
      alert('Failed to start authentication. Please try again.');
    } finally {
      setAuthenticatingProfileId(null);
    }
  };

  const toggleTokenEntry = (profileId: string) => {
    if (expandedTokenProfileId === profileId) {
      setExpandedTokenProfileId(null);
      setManualToken('');
      setManualTokenEmail('');
      setShowManualToken(false);
    } else {
      setExpandedTokenProfileId(profileId);
      setManualToken('');
      setManualTokenEmail('');
      setShowManualToken(false);
    }
  };

  const handleSaveManualToken = async (profileId: string) => {
    if (!manualToken.trim()) return;

    setSavingTokenProfileId(profileId);
    try {
      const result = await window.electronAPI.setClaudeProfileToken(
        profileId,
        manualToken.trim(),
        manualTokenEmail.trim() || undefined
      );
      if (result.success) {
        await loadClaudeProfiles();
        setExpandedTokenProfileId(null);
        setManualToken('');
        setManualTokenEmail('');
        setShowManualToken(false);
      } else {
        alert(`Failed to save token: ${result.error || 'Please try again.'}`);
      }
    } catch (err) {
      console.error('Failed to save token:', err);
      alert('Failed to save token. Please try again.');
    } finally {
      setSavingTokenProfileId(null);
    }
  };

  // Validate Azure Foundry URL
  const validateAzureUrl = (url: string): boolean => {
    if (!url) {
      setAzureUrlError(null);
      return false;
    }
    try {
      new URL(url);
      if (!url.endsWith('/anthropic')) {
        setAzureUrlError('Base URL must end with /anthropic');
        return false;
      }
      setAzureUrlError(null);
      return true;
    } catch {
      setAzureUrlError('Invalid URL format');
      return false;
    }
  };

  // Handle Azure Foundry profile creation
  const handleAddAzureProfile = async () => {
    if (!newAzureProfileName.trim() || !newAzureApiKey.trim() || !newAzureBaseUrl.trim()) return;
    if (!validateAzureUrl(newAzureBaseUrl)) return;

    setIsSavingAzureProfile(true);
    try {
      const profileName = newAzureProfileName.trim();
      const profileSlug = profileName.toLowerCase().replace(/\s+/g, '-');

      const result = await window.electronAPI.saveClaudeProfile({
        id: `azure-${Date.now()}`,
        name: profileName,
        configDir: `~/.claude-profiles/${profileSlug}`,
        isDefault: false,
        createdAt: new Date(),
        proxyEnabled: true,
        proxyBaseUrl: newAzureBaseUrl.trim(),
        proxyApiKey: newAzureApiKey.trim()
      });

      if (result.success) {
        await loadClaudeProfiles();
        // Reset form
        setIsAddingAzureProfile(false);
        setNewAzureProfileName('');
        setNewAzureApiKey('');
        setNewAzureBaseUrl('');
        setShowNewAzureApiKey(false);
        setAzureUrlError(null);
      } else {
        alert(`Failed to create Azure profile: ${result.error || 'Please try again.'}`);
      }
    } catch (err) {
      console.error('Failed to add Azure profile:', err);
      alert('Failed to create Azure profile. Please try again.');
    } finally {
      setIsSavingAzureProfile(false);
    }
  };

  // Cancel Azure profile creation
  const handleCancelAzureProfile = () => {
    setIsAddingAzureProfile(false);
    setNewAzureProfileName('');
    setNewAzureApiKey('');
    setNewAzureBaseUrl('');
    setShowNewAzureApiKey(false);
    setAzureUrlError(null);
  };

  // Check if profile is authenticated based on its type
  const isProfileAuthenticated = (profile: ClaudeProfile): boolean => {
    if (profile.proxyEnabled) {
      // Azure Foundry profile - authenticated if has API key and base URL
      return !!(profile.proxyApiKey && profile.proxyBaseUrl);
    }
    // OAuth profile - authenticated if has OAuth token OR (is default AND has configDir)
    return !!(profile.oauthToken || (profile.isDefault && profile.configDir));
  };

  // Get profile type label
  const getProfileTypeLabel = (profile: ClaudeProfile): string => {
    if (profile.proxyEnabled) {
      return 'Azure Foundry';
    }
    return 'OAuth';
  };

  // Validate global Azure Foundry URL
  const validateGlobalAzureUrl = (url: string): boolean => {
    if (!url) {
      setGlobalAzureUrlError(null);
      return true; // Empty is valid (optional field)
    }
    try {
      new URL(url);
      if (!url.endsWith('/anthropic')) {
        setGlobalAzureUrlError('Base URL must end with /anthropic');
        return false;
      }
      setGlobalAzureUrlError(null);
      return true;
    } catch {
      setGlobalAzureUrlError('Invalid URL format');
      return false;
    }
  };

  // Load auto-swap settings
  const loadAutoSwitchSettings = async () => {
    setIsLoadingAutoSwitch(true);
    try {
      const result = await window.electronAPI.getAutoSwitchSettings();
      if (result.success && result.data) {
        setAutoSwitchSettings(result.data);
      }
    } catch (err) {
      console.error('Failed to load auto-switch settings:', err);
    } finally {
      setIsLoadingAutoSwitch(false);
    }
  };

  // Update auto-swap settings
  const handleUpdateAutoSwitch = async (updates: Partial<ClaudeAutoSwitchSettings>) => {
    setIsLoadingAutoSwitch(true);
    try {
      const result = await window.electronAPI.updateAutoSwitchSettings(updates);
      if (result.success) {
        await loadAutoSwitchSettings();
      } else {
        alert(`Failed to update settings: ${result.error || 'Please try again.'}`);
      }
    } catch (err) {
      console.error('Failed to update auto-switch settings:', err);
      alert('Failed to update settings. Please try again.');
    } finally {
      setIsLoadingAutoSwitch(false);
    }
  };

  return (
    <SettingsSection
      title={t('integrations.title')}
      description={t('integrations.description')}
    >
      <div className="space-y-6">
        {/* Claude Accounts Section */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-muted-foreground" />
            <h4 className="text-sm font-semibold text-foreground">{t('integrations.claudeAccounts')}</h4>
          </div>

          <div className="rounded-lg bg-muted/30 border border-border p-4">
            <p className="text-sm text-muted-foreground mb-4">
              {t('integrations.claudeAccountsDescription')}
            </p>

            {/* Accounts list */}
            {isLoadingProfiles ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : claudeProfiles.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border p-4 text-center mb-4">
                <p className="text-sm text-muted-foreground">{t('integrations.noAccountsYet')}</p>
              </div>
            ) : (
              <div className="space-y-2 mb-4">
                {claudeProfiles.map((profile) => (
                  <div
                    key={profile.id}
                    className={cn(
                      "rounded-lg border transition-colors",
                      profile.id === activeProfileId
                        ? "border-primary bg-primary/5"
                        : "border-border bg-background"
                    )}
                  >
                    <div className={cn(
                      "flex items-center justify-between p-3",
                      expandedTokenProfileId !== profile.id && "hover:bg-muted/50"
                    )}>
                      <div className="flex items-center gap-3">
                        <div className={cn(
                          "h-7 w-7 rounded-full flex items-center justify-center text-xs font-medium shrink-0",
                          profile.id === activeProfileId
                            ? "bg-primary text-primary-foreground"
                            : profile.proxyEnabled
                              ? "bg-blue-500/20 text-blue-500"
                              : "bg-muted text-muted-foreground"
                        )}>
                          {profile.proxyEnabled ? (
                            <Cloud className="h-3.5 w-3.5" />
                          ) : (
                            (editingProfileId === profile.id ? editingProfileName : profile.name).charAt(0).toUpperCase()
                          )}
                        </div>
                        <div className="min-w-0">
                          {editingProfileId === profile.id ? (
                            <div className="flex items-center gap-2">
                              <Input
                                value={editingProfileName}
                                onChange={(e) => setEditingProfileName(e.target.value)}
                                className="h-7 text-sm w-40"
                                autoFocus
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') handleRenameProfile();
                                  if (e.key === 'Escape') cancelEditingProfile();
                                }}
                              />
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={handleRenameProfile}
                                className="h-7 w-7 text-success hover:text-success hover:bg-success/10"
                                aria-label={t('common:accessibility.saveEditAriaLabel')}
                              >
                                <Check className="h-3 w-3" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={cancelEditingProfile}
                                className="h-7 w-7 text-muted-foreground hover:text-foreground"
                                aria-label={t('common:accessibility.cancelEditAriaLabel')}
                              >
                                <X className="h-3 w-3" />
                              </Button>
                            </div>
                          ) : (
                            <>
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="text-sm font-medium text-foreground">{profile.name}</span>
                                {/* Profile type badge */}
                                <span className={cn(
                                  "text-xs px-1.5 py-0.5 rounded flex items-center gap-1",
                                  profile.proxyEnabled
                                    ? "bg-blue-500/20 text-blue-600 dark:text-blue-400"
                                    : "bg-muted text-muted-foreground"
                                )}>
                                  {profile.proxyEnabled ? (
                                    <Cloud className="h-3 w-3" />
                                  ) : (
                                    <Users className="h-3 w-3" />
                                  )}
                                  {getProfileTypeLabel(profile)}
                                </span>
                                {profile.isDefault && (
                                  <span className="text-xs bg-muted px-1.5 py-0.5 rounded">{t('integrations.default')}</span>
                                )}
                                {profile.id === activeProfileId && (
                                  <span className="text-xs bg-primary/20 text-primary px-1.5 py-0.5 rounded flex items-center gap-1">
                                    <Star className="h-3 w-3" />
                                    {t('integrations.active')}
                                  </span>
                                )}
                                {isProfileAuthenticated(profile) ? (
                                  <span className="text-xs bg-success/20 text-success px-1.5 py-0.5 rounded flex items-center gap-1">
                                    <Check className="h-3 w-3" />
                                    {t('integrations.authenticated')}
                                  </span>
                                ) : (
                                  <span className="text-xs bg-warning/20 text-warning px-1.5 py-0.5 rounded">
                                    {t('integrations.needsAuth')}
                                  </span>
                                )}
                              </div>
                              {profile.email && (
                                <span className="text-xs text-muted-foreground">{profile.email}</span>
                              )}
                              {/* Show Azure endpoint for proxy profiles */}
                              {profile.proxyEnabled && profile.proxyBaseUrl && (
                                <div className="text-xs text-muted-foreground truncate max-w-[250px]" title={profile.proxyBaseUrl}>
                                  {profile.proxyBaseUrl}
                                </div>
                              )}
                            </>
                          )}
                        </div>
                      </div>
                      {editingProfileId !== profile.id && (
                        <div className="flex items-center gap-1">
                          {/* Authenticate button - only for OAuth profiles, not Azure Foundry */}
                          {!profile.proxyEnabled && (
                            <>
                              {!isProfileAuthenticated(profile) ? (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => handleAuthenticateProfile(profile.id)}
                                  disabled={authenticatingProfileId === profile.id}
                                  className="gap-1 h-7 text-xs"
                                >
                                  {authenticatingProfileId === profile.id ? (
                                    <Loader2 className="h-3 w-3 animate-spin" />
                                  ) : (
                                    <LogIn className="h-3 w-3" />
                                  )}
                                  {t('integrations.authenticate')}
                                </Button>
                              ) : (
                                /* Re-authenticate button for already authenticated OAuth profiles */
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  onClick={() => handleAuthenticateProfile(profile.id)}
                                  disabled={authenticatingProfileId === profile.id}
                                  className="h-7 w-7 text-muted-foreground hover:text-foreground"
                                  title="Re-authenticate profile"
                                >
                                  {authenticatingProfileId === profile.id ? (
                                    <Loader2 className="h-3 w-3 animate-spin" />
                                  ) : (
                                    <RefreshCw className="h-3 w-3" />
                                  )}
                                </Button>
                              )}
                            </>
                          )}
                          {profile.id !== activeProfileId && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleSetActiveProfile(profile.id)}
                              className="gap-1 h-7 text-xs"
                            >
                              <Check className="h-3 w-3" />
                              {t('integrations.setActive')}
                            </Button>
                          )}
                          {/* Toggle token entry button */}
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => toggleTokenEntry(profile.id)}
                                className="h-7 w-7 text-muted-foreground hover:text-foreground"
                                aria-label={expandedTokenProfileId === profile.id ? t('common:accessibility.collapseAriaLabel') : t('common:accessibility.expandAriaLabel')}
                              >
                                {expandedTokenProfileId === profile.id ? (
                                  <ChevronDown className="h-3 w-3" />
                                ) : (
                                  <ChevronRight className="h-3 w-3" />
                                )}
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>
                              {expandedTokenProfileId === profile.id ? t('common:accessibility.hideTokenEntryAriaLabel') : t('common:accessibility.enterTokenManuallyAriaLabel')}
                            </TooltipContent>
                          </Tooltip>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => startEditingProfile(profile)}
                                className="h-7 w-7 text-muted-foreground hover:text-foreground"
                                aria-label={t('common:accessibility.renameAriaLabel')}
                              >
                                <Pencil className="h-3 w-3" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>{t('common:accessibility.renameProfileAriaLabel')}</TooltipContent>
                          </Tooltip>
                          {!profile.isDefault && (
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  onClick={() => handleDeleteProfile(profile.id)}
                                  disabled={deletingProfileId === profile.id}
                                  className="h-7 w-7 text-destructive hover:text-destructive hover:bg-destructive/10"
                                  aria-label={t('common:accessibility.deleteAriaLabel')}
                                >
                                  {deletingProfileId === profile.id ? (
                                    <Loader2 className="h-3 w-3 animate-spin" />
                                  ) : (
                                    <Trash2 className="h-3 w-3" />
                                  )}
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>{t('common:accessibility.deleteProfileAriaLabel')}</TooltipContent>
                            </Tooltip>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Expanded token entry section */}
                    {expandedTokenProfileId === profile.id && (
                      <div className="px-3 pb-3 pt-0 border-t border-border/50 mt-0">
                        <div className="bg-muted/30 rounded-lg p-3 mt-3 space-y-3">
                          <div className="flex items-center justify-between">
                            <Label className="text-xs font-medium text-muted-foreground">
                              {t('integrations.manualTokenEntry')}
                            </Label>
                            <span className="text-xs text-muted-foreground">
                              {t('integrations.runSetupToken')}
                            </span>
                          </div>

                          <div className="space-y-2">
                            <div className="relative">
                              <Input
                                type={showManualToken ? 'text' : 'password'}
                                placeholder={t('integrations.tokenPlaceholder')}
                                value={manualToken}
                                onChange={(e) => setManualToken(e.target.value)}
                                className="pr-10 font-mono text-xs h-8"
                              />
                              <button
                                type="button"
                                onClick={() => setShowManualToken(!showManualToken)}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                              >
                                {showManualToken ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                              </button>
                            </div>

                            <Input
                              type="email"
                              placeholder={t('integrations.emailPlaceholder')}
                              value={manualTokenEmail}
                              onChange={(e) => setManualTokenEmail(e.target.value)}
                              className="text-xs h-8"
                            />
                          </div>

                          <div className="flex items-center justify-end gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => toggleTokenEntry(profile.id)}
                              className="h-7 text-xs"
                            >
                              {tCommon('buttons.cancel')}
                            </Button>
                            <Button
                              size="sm"
                              onClick={() => handleSaveManualToken(profile.id)}
                              disabled={!manualToken.trim() || savingTokenProfileId === profile.id}
                              className="h-7 text-xs gap-1"
                            >
                              {savingTokenProfileId === profile.id ? (
                                <Loader2 className="h-3 w-3 animate-spin" />
                              ) : (
                                <Check className="h-3 w-3" />
                              )}
                              {t('integrations.saveToken')}
                            </Button>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Add new account section */}
            <div className="space-y-3">
              {/* Toggle between OAuth and Azure Foundry */}
              <div className="flex items-center gap-2">
                <Button
                  variant={!isAddingAzureProfile ? "default" : "outline"}
                  size="sm"
                  onClick={() => setIsAddingAzureProfile(false)}
                  className="gap-1"
                >
                  <Users className="h-3 w-3" />
                  OAuth
                </Button>
                <Button
                  variant={isAddingAzureProfile ? "default" : "outline"}
                  size="sm"
                  onClick={() => setIsAddingAzureProfile(true)}
                  className="gap-1"
                >
                  <Cloud className="h-3 w-3" />
                  Azure Foundry
                </Button>
              </div>

              {/* OAuth profile form */}
              {!isAddingAzureProfile && (
                <div className="flex items-center gap-2">
                  <Input
                    placeholder={t('integrations.accountNamePlaceholder')}
                    value={newProfileName}
                    onChange={(e) => setNewProfileName(e.target.value)}
                    className="flex-1 h-8 text-sm"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && newProfileName.trim()) {
                        handleAddProfile();
                      }
                    }}
                  />
                  <Button
                    onClick={handleAddProfile}
                    disabled={!newProfileName.trim() || isAddingProfile}
                    size="sm"
                    className="gap-1 shrink-0"
                  >
                    {isAddingProfile ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <Plus className="h-3 w-3" />
                    )}
                    {tCommon('buttons.add')}
                  </Button>
                </div>
              )}

              {/* Azure Foundry profile form */}
              {isAddingAzureProfile && (
                <div className="bg-blue-500/5 border border-blue-500/20 rounded-lg p-3 space-y-3">
                  <div className="flex items-center gap-2 text-sm font-medium text-blue-600 dark:text-blue-400">
                    <Cloud className="h-4 w-4" />
                    {t('integrations.addAzureProfile') || 'Add Azure Foundry Profile'}
                  </div>

                  <div className="space-y-2">
                    <Input
                      placeholder={t('integrations.profileNamePlaceholder') || 'Profile name (e.g., "Work Azure")'}
                      value={newAzureProfileName}
                      onChange={(e) => setNewAzureProfileName(e.target.value)}
                      className="h-8 text-sm"
                    />

                    <div className="relative">
                      <Input
                        type={showNewAzureApiKey ? 'text' : 'password'}
                        placeholder={t('integrations.azureApiKeyPlaceholder') || 'Azure Foundry API Key'}
                        value={newAzureApiKey}
                        onChange={(e) => setNewAzureApiKey(e.target.value)}
                        className="h-8 text-sm pr-10"
                      />
                      <button
                        type="button"
                        onClick={() => setShowNewAzureApiKey(!showNewAzureApiKey)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      >
                        {showNewAzureApiKey ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                      </button>
                    </div>

                    <Input
                      placeholder="https://your-resource.openai.azure.com/anthropic"
                      value={newAzureBaseUrl}
                      onChange={(e) => {
                        setNewAzureBaseUrl(e.target.value);
                        validateAzureUrl(e.target.value);
                      }}
                      className={cn("h-8 text-sm", azureUrlError && "border-destructive")}
                    />
                    {azureUrlError && (
                      <p className="text-xs text-destructive">{azureUrlError}</p>
                    )}
                  </div>

                  <div className="flex items-center justify-end gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleCancelAzureProfile}
                      className="h-7 text-xs"
                    >
                      {tCommon('buttons.cancel')}
                    </Button>
                    <Button
                      size="sm"
                      onClick={handleAddAzureProfile}
                      disabled={!newAzureProfileName.trim() || !newAzureApiKey.trim() || !newAzureBaseUrl.trim() || !!azureUrlError || isSavingAzureProfile}
                      className="h-7 text-xs gap-1"
                    >
                      {isSavingAzureProfile ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <Plus className="h-3 w-3" />
                      )}
                      {t('integrations.createProfile') || 'Create Profile'}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Auto-Switch Settings Section */}
        {claudeProfiles.length > 1 && (
          <div className="space-y-4 pt-6 border-t border-border">
            <div className="flex items-center gap-2">
              <RefreshCw className="h-4 w-4 text-muted-foreground" />
              <h4 className="text-sm font-semibold text-foreground">{t('integrations.autoSwitching')}</h4>
            </div>

            <div className="rounded-lg bg-muted/30 border border-border p-4 space-y-4">
              <p className="text-sm text-muted-foreground">
                {t('integrations.autoSwitchingDescription')}
              </p>

              {/* Master toggle */}
              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-sm font-medium">{t('integrations.enableAutoSwitching')}</Label>
                  <p className="text-xs text-muted-foreground mt-1">
                    {t('integrations.masterSwitch')}
                  </p>
                </div>
                <Switch
                  checked={autoSwitchSettings?.enabled ?? false}
                  onCheckedChange={(enabled) => handleUpdateAutoSwitch({ enabled })}
                  disabled={isLoadingAutoSwitch}
                />
              </div>

              {autoSwitchSettings?.enabled && (
                <>
                  {/* Proactive Monitoring Section */}
                  <div className="pl-6 space-y-4 pt-2 border-l-2 border-primary/20">
                    <div className="flex items-center justify-between">
                      <div>
                        <Label className="text-sm font-medium flex items-center gap-2">
                          <Activity className="h-3.5 w-3.5" />
                          {t('integrations.proactiveMonitoring')}
                        </Label>
                        <p className="text-xs text-muted-foreground mt-1">
                          {t('integrations.proactiveDescription')}
                        </p>
                      </div>
                      <Switch
                        checked={autoSwitchSettings?.proactiveSwapEnabled ?? true}
                        onCheckedChange={(value) => handleUpdateAutoSwitch({ proactiveSwapEnabled: value })}
                        disabled={isLoadingAutoSwitch}
                      />
                    </div>

                    {autoSwitchSettings?.proactiveSwapEnabled && (
                      <>
                        {/* Check interval */}
                        <div className="space-y-2">
                          <Label className="text-sm">{t('integrations.checkUsageEvery')}</Label>
                          <select
                            className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm"
                            value={autoSwitchSettings?.usageCheckInterval ?? 30000}
                            onChange={(e) => handleUpdateAutoSwitch({ usageCheckInterval: parseInt(e.target.value) })}
                            disabled={isLoadingAutoSwitch}
                          >
                            <option value={15000}>{t('integrations.seconds15')}</option>
                            <option value={30000}>{t('integrations.seconds30')}</option>
                            <option value={60000}>{t('integrations.minute1')}</option>
                            <option value={0}>{t('integrations.disabled')}</option>
                          </select>
                        </div>

                        {/* Session threshold */}
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <Label className="text-sm">{t('integrations.sessionThreshold')}</Label>
                            <span className="text-sm font-mono">{autoSwitchSettings?.sessionThreshold ?? 95}%</span>
                          </div>
                          <input
                            type="range"
                            min="70"
                            max="99"
                            step="1"
                            value={autoSwitchSettings?.sessionThreshold ?? 95}
                            onChange={(e) => handleUpdateAutoSwitch({ sessionThreshold: parseInt(e.target.value) })}
                            disabled={isLoadingAutoSwitch}
                            className="w-full"
                          />
                          <p className="text-xs text-muted-foreground">
                            {t('integrations.sessionThresholdDescription')}
                          </p>
                        </div>

                        {/* Weekly threshold */}
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <Label className="text-sm">{t('integrations.weeklyThreshold')}</Label>
                            <span className="text-sm font-mono">{autoSwitchSettings?.weeklyThreshold ?? 99}%</span>
                          </div>
                          <input
                            type="range"
                            min="70"
                            max="99"
                            step="1"
                            value={autoSwitchSettings?.weeklyThreshold ?? 99}
                            onChange={(e) => handleUpdateAutoSwitch({ weeklyThreshold: parseInt(e.target.value) })}
                            disabled={isLoadingAutoSwitch}
                            className="w-full"
                          />
                          <p className="text-xs text-muted-foreground">
                            {t('integrations.weeklyThresholdDescription')}
                          </p>
                        </div>
                      </>
                    )}
                  </div>

                  {/* Reactive Recovery Section */}
                  <div className="pl-6 space-y-4 pt-2 border-l-2 border-orange-500/20">
                    <div className="flex items-center justify-between">
                      <div>
                        <Label className="text-sm font-medium flex items-center gap-2">
                          <AlertCircle className="h-3.5 w-3.5" />
                          {t('integrations.reactiveRecovery')}
                        </Label>
                        <p className="text-xs text-muted-foreground mt-1">
                          {t('integrations.reactiveDescription')}
                        </p>
                      </div>
                      <Switch
                        checked={autoSwitchSettings?.autoSwitchOnRateLimit ?? false}
                        onCheckedChange={(value) => handleUpdateAutoSwitch({ autoSwitchOnRateLimit: value })}
                        disabled={isLoadingAutoSwitch}
                      />
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {/* Default Authentication Section */}
        <div className="space-y-4 pt-4 border-t border-border">
          <div className="flex items-center gap-2">
            <Server className="h-4 w-4 text-muted-foreground" />
            <h4 className="text-sm font-semibold text-foreground">
              {t('integrations.defaultAuth') || 'Default Authentication'}
            </h4>
          </div>

          <div className="rounded-lg bg-muted/30 border border-border p-4 space-y-4">
            <p className="text-sm text-muted-foreground">
              {t('integrations.defaultAuthDescription') || 'Configure default authentication for new projects that don\'t have specific settings.'}
            </p>

            {/* Default Auth Mode Selector */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">
                {t('integrations.defaultAuthMode') || 'Default Authentication Mode'}
              </Label>
              <select
                className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm"
                value={settings.defaultAuthMode || 'oauth'}
                onChange={(e) =>
                  onSettingsChange({ ...settings, defaultAuthMode: e.target.value as 'oauth' | 'azure-foundry' | 'auth-token' })
                }
              >
                <option value="oauth">OAuth (Recommended)</option>
                <option value="azure-foundry">Azure Foundry (Enterprise)</option>
                <option value="auth-token">Auth Token (CCR/Proxy)</option>
              </select>
            </div>

            {/* Azure Foundry Default Settings - Show when Azure Foundry is selected */}
            {settings.defaultAuthMode === 'azure-foundry' && (
              <div className="bg-blue-500/5 border border-blue-500/20 rounded-lg p-3 space-y-3">
                <div className="flex items-center gap-2 text-sm font-medium text-blue-600 dark:text-blue-400">
                  <Cloud className="h-4 w-4" />
                  {t('integrations.azureFoundryDefaults') || 'Azure Foundry Default Settings'}
                </div>

                <div className="space-y-3">
                  {/* API Key */}
                  <div className="space-y-1">
                    <Label className="text-xs">
                      {t('integrations.azureApiKey') || 'API Key'}
                    </Label>
                    <div className="relative">
                      <Input
                        type={showGlobalAzureApiKey ? 'text' : 'password'}
                        placeholder={t('integrations.azureApiKeyPlaceholder') || 'Azure Foundry API Key'}
                        value={settings.azureFoundryApiKey || ''}
                        onChange={(e) =>
                          onSettingsChange({ ...settings, azureFoundryApiKey: e.target.value || undefined })
                        }
                        className="h-8 text-sm pr-10"
                      />
                      <button
                        type="button"
                        onClick={() => setShowGlobalAzureApiKey(!showGlobalAzureApiKey)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      >
                        {showGlobalAzureApiKey ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                      </button>
                    </div>
                  </div>

                  {/* Base URL */}
                  <div className="space-y-1">
                    <Label className="text-xs">
                      {t('integrations.azureBaseUrl') || 'Base URL'}
                    </Label>
                    <Input
                      placeholder="https://your-resource.openai.azure.com/anthropic"
                      value={settings.azureFoundryBaseUrl || ''}
                      onChange={(e) => {
                        const url = e.target.value;
                        onSettingsChange({ ...settings, azureFoundryBaseUrl: url || undefined });
                        validateGlobalAzureUrl(url);
                      }}
                      className={cn("h-8 text-sm", globalAzureUrlError && "border-destructive")}
                    />
                    {globalAzureUrlError && (
                      <p className="text-xs text-destructive">{globalAzureUrlError}</p>
                    )}
                  </div>

                  {/* Resource Name */}
                  <div className="space-y-1">
                    <Label className="text-xs">
                      {t('integrations.azureResourceName') || 'Resource Name'}
                    </Label>
                    <Input
                      placeholder="your-azure-resource"
                      value={settings.azureFoundryResourceName || ''}
                      onChange={(e) =>
                        onSettingsChange({ ...settings, azureFoundryResourceName: e.target.value || undefined })
                      }
                      className="h-8 text-sm"
                    />
                  </div>

                  {/* Model Deployments */}
                  <div className="pt-2 border-t border-border/50">
                    <Label className="text-xs font-medium">
                      {t('integrations.modelDeployments') || 'Model Deployment Names'}
                    </Label>
                    <p className="text-xs text-muted-foreground mb-2">
                      {t('integrations.modelDeploymentsDescription') || 'Custom deployment names for your Azure Foundry models'}
                    </p>
                    <div className="grid grid-cols-3 gap-2">
                      <div className="space-y-1">
                        <Label className="text-xs text-muted-foreground">Sonnet</Label>
                        <Input
                          placeholder="claude-sonnet-4-5"
                          value={settings.azureFoundrySonnetModel || ''}
                          onChange={(e) =>
                            onSettingsChange({ ...settings, azureFoundrySonnetModel: e.target.value || undefined })
                          }
                          className="h-7 text-xs"
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs text-muted-foreground">Haiku</Label>
                        <Input
                          placeholder="claude-haiku-4-5"
                          value={settings.azureFoundryHaikuModel || ''}
                          onChange={(e) =>
                            onSettingsChange({ ...settings, azureFoundryHaikuModel: e.target.value || undefined })
                          }
                          className="h-7 text-xs"
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs text-muted-foreground">Opus</Label>
                        <Input
                          placeholder="claude-opus-4-5"
                          value={settings.azureFoundryOpusModel || ''}
                          onChange={(e) =>
                            onSettingsChange({ ...settings, azureFoundryOpusModel: e.target.value || undefined })
                          }
                          className="h-7 text-xs"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* API Keys Section */}
        <div className="space-y-4 pt-4 border-t border-border">
          <div className="flex items-center gap-2">
            <Key className="h-4 w-4 text-muted-foreground" />
            <h4 className="text-sm font-semibold text-foreground">{t('integrations.apiKeys')}</h4>
          </div>

          <div className="rounded-lg bg-info/10 border border-info/30 p-3">
            <div className="flex items-start gap-2">
              <Info className="h-4 w-4 text-info shrink-0 mt-0.5" />
              <p className="text-xs text-muted-foreground">
                {t('integrations.apiKeysInfo')}
              </p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="globalOpenAIKey" className="text-sm font-medium text-foreground">
                {t('integrations.openaiKey')}
              </Label>
              <p className="text-xs text-muted-foreground">
                {t('integrations.openaiKeyDescription')}
              </p>
              <div className="relative max-w-lg">
                <Input
                  id="globalOpenAIKey"
                  type={showGlobalOpenAIKey ? 'text' : 'password'}
                  placeholder="sk-..."
                  value={settings.globalOpenAIApiKey || ''}
                  onChange={(e) =>
                    onSettingsChange({ ...settings, globalOpenAIApiKey: e.target.value || undefined })
                  }
                  className="pr-10 font-mono text-sm"
                />
                <button
                  type="button"
                  onClick={() => setShowGlobalOpenAIKey(!showGlobalOpenAIKey)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showGlobalOpenAIKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </SettingsSection>
  );
}
