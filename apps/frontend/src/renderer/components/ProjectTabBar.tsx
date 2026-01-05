import { useEffect, useRef, useState, useCallback } from 'react';
import { Plus, ChevronDown, X, FolderOpen } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { cn } from '../lib/utils';
import { Button } from './ui/button';
import { SortableProjectTab } from './SortableProjectTab';
import { UsageIndicator } from './UsageIndicator';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from './ui/dropdown-menu';
import { Tooltip, TooltipContent, TooltipTrigger } from './ui/tooltip';
import type { Project } from '../../shared/types';

// Approximate width for each tab (used for overflow calculation)
const TAB_WIDTH = 160;
// Minimum tabs to always show (before overflow kicks in)
const MIN_VISIBLE_TABS = 2;
// Width reserved for action buttons (usage indicator, add, overflow)
const ACTIONS_WIDTH = 140;

interface ProjectTabBarProps {
  projects: Project[];
  activeProjectId: string | null;
  onProjectSelect: (projectId: string) => void;
  onProjectClose: (projectId: string) => void;
  onAddProject: () => void;
  className?: string;
  onSettingsClick?: () => void;
}

export function ProjectTabBar({
  projects,
  activeProjectId,
  onProjectSelect,
  onProjectClose,
  onAddProject,
  className,
  onSettingsClick
}: ProjectTabBarProps) {
  const { t } = useTranslation('common');
  const containerRef = useRef<HTMLDivElement>(null);
  const [maxVisibleTabs, setMaxVisibleTabs] = useState<number>(projects.length);

  // Calculate how many tabs can fit
  const calculateVisibleTabs = useCallback(() => {
    if (!containerRef.current) return;

    const containerWidth = containerRef.current.offsetWidth;
    const availableWidth = containerWidth - ACTIONS_WIDTH;
    const calculatedMax = Math.max(MIN_VISIBLE_TABS, Math.floor(availableWidth / TAB_WIDTH));

    setMaxVisibleTabs(calculatedMax);
  }, []);

  // Observe container resize
  useEffect(() => {
    calculateVisibleTabs();

    const resizeObserver = new ResizeObserver(() => {
      calculateVisibleTabs();
    });

    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    return () => resizeObserver.disconnect();
  }, [calculateVisibleTabs]);

  // Recalculate when projects change
  useEffect(() => {
    calculateVisibleTabs();
  }, [projects.length, calculateVisibleTabs]);

  // Keyboard shortcuts for tab navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        (e.target as HTMLElement)?.isContentEditable
      ) {
        return;
      }

      const isMod = e.metaKey || e.ctrlKey;
      if (!isMod) return;

      // Cmd/Ctrl + 1-9: Switch to tab N
      if (e.key >= '1' && e.key <= '9') {
        e.preventDefault();
        const index = parseInt(e.key) - 1;
        if (index < projects.length) {
          onProjectSelect(projects[index].id);
        }
        return;
      }

      // Cmd/Ctrl + Tab: Next tab
      // Cmd/Ctrl + Shift + Tab: Previous tab
      if (e.key === 'Tab') {
        e.preventDefault();
        const currentIndex = projects.findIndex((p) => p.id === activeProjectId);
        if (currentIndex === -1 || projects.length === 0) return;

        const nextIndex = e.shiftKey
          ? (currentIndex - 1 + projects.length) % projects.length
          : (currentIndex + 1) % projects.length;
        onProjectSelect(projects[nextIndex].id);
        return;
      }

      // Cmd/Ctrl + W: Close current tab (only if more than one tab)
      if (e.key === 'w' && activeProjectId && projects.length > 1) {
        e.preventDefault();
        onProjectClose(activeProjectId);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [projects, activeProjectId, onProjectSelect, onProjectClose]);

  if (projects.length === 0) {
    return null;
  }

  // Determine which tabs are visible and which go to overflow
  const activeIndex = projects.findIndex((p) => p.id === activeProjectId);
  const needsOverflow = projects.length > maxVisibleTabs;

  let visibleProjects: Project[];
  let overflowProjects: Project[];

  if (!needsOverflow) {
    visibleProjects = projects;
    overflowProjects = [];
  } else {
    // Always ensure the active tab is visible
    // Strategy: Show first (maxVisibleTabs - 1) tabs, but if active is in overflow, swap it in
    const visibleCount = maxVisibleTabs;

    if (activeIndex < visibleCount) {
      // Active tab is already in visible range
      visibleProjects = projects.slice(0, visibleCount);
      overflowProjects = projects.slice(visibleCount);
    } else {
      // Active tab is in overflow - include it at the end of visible tabs
      visibleProjects = [
        ...projects.slice(0, visibleCount - 1),
        projects[activeIndex]
      ];
      overflowProjects = projects.filter((p, i) =>
        i >= visibleCount - 1 && i !== activeIndex
      );
    }
  }

  return (
    <div
      ref={containerRef}
      className={cn(
        'flex items-center border-b border-border bg-background',
        className
      )}
    >
      {/* Visible tabs */}
      <div className="flex items-center min-w-0 flex-shrink">
        {visibleProjects.map((project, index) => {
          const isActiveTab = activeProjectId === project.id;
          // Find original index for keyboard shortcut
          const originalIndex = projects.findIndex((p) => p.id === project.id);
          return (
            <SortableProjectTab
              key={project.id}
              project={project}
              isActive={isActiveTab}
              canClose={projects.length > 1}
              tabIndex={originalIndex}
              onSelect={() => onProjectSelect(project.id)}
              onClose={(e) => {
                e.stopPropagation();
                onProjectClose(project.id);
              }}
              onSettingsClick={isActiveTab ? onSettingsClick : undefined}
            />
          );
        })}
      </div>

      {/* Overflow menu */}
      {needsOverflow && overflowProjects.length > 0 && (
        <DropdownMenu>
          <Tooltip delayDuration={200}>
            <TooltipTrigger asChild>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className={cn(
                    'h-8 px-2 gap-1 flex-shrink-0',
                    'text-muted-foreground hover:text-foreground',
                    'border-r border-border'
                  )}
                >
                  <span className="text-xs font-medium">+{overflowProjects.length}</span>
                  <ChevronDown className="h-3 w-3" />
                </Button>
              </DropdownMenuTrigger>
            </TooltipTrigger>
            <TooltipContent side="bottom">
              {t('projectTab.moreProjects', { count: overflowProjects.length })}
            </TooltipContent>
          </Tooltip>

          <DropdownMenuContent
            align="start"
            className="w-64 max-h-80 overflow-y-auto"
          >
            <div className="px-2 py-1.5 text-xs font-medium text-muted-foreground">
              {t('projectTab.otherProjects', { count: overflowProjects.length })}
            </div>
            <DropdownMenuSeparator />
            {overflowProjects.map((project) => {
              const originalIndex = projects.findIndex((p) => p.id === project.id);
              const shortcut = originalIndex < 9 ? `⌘${originalIndex + 1}` : '';

              return (
                <DropdownMenuItem
                  key={project.id}
                  className="flex items-center justify-between gap-2 cursor-pointer"
                  onClick={() => onProjectSelect(project.id)}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <FolderOpen className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                    <span className="truncate">{project.name}</span>
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    {shortcut && (
                      <kbd className="px-1.5 py-0.5 text-[10px] bg-muted rounded border border-border font-mono">
                        {shortcut}
                      </kbd>
                    )}
                    {projects.length > 1 && (
                      <button
                        type="button"
                        className={cn(
                          'h-5 w-5 rounded flex items-center justify-center',
                          'text-muted-foreground hover:text-destructive',
                          'hover:bg-destructive/10 transition-colors'
                        )}
                        onClick={(e) => {
                          e.stopPropagation();
                          onProjectClose(project.id);
                        }}
                        aria-label={t('projectTab.closeTab')}
                      >
                        <X className="h-3 w-3" />
                      </button>
                    )}
                  </div>
                </DropdownMenuItem>
              );
            })}
          </DropdownMenuContent>
        </DropdownMenu>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-2 px-2 py-1 ml-auto flex-shrink-0">
        <UsageIndicator />
        <Tooltip delayDuration={200}>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={onAddProject}
            >
              <Plus className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            {t('projectTab.addProject', 'Add Project')}
          </TooltipContent>
        </Tooltip>
      </div>
    </div>
  );
}
