import { useProjectStore } from '../stores/project-store';

/**
 * Hook to get the current active project's path
 * Returns the path of the active project tab, or null if no project is active
 */
export function useProjectPath() {
  const getActiveProject = useProjectStore((state) => state.getActiveProject);
  const activeProject = getActiveProject();

  return {
    projectPath: activeProject?.path ?? null,
    projectId: activeProject?.id ?? null,
    projectName: activeProject?.name ?? null,
  };
}

export default useProjectPath;
