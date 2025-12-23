import { IPC_CHANNELS } from '../../../shared/constants';
import type {
  Skill,
  SkillInstallOutput,
  SkillContent,
  IPCResult
} from '../../../shared/types';
import { invokeIpc } from './ipc-utils';

/**
 * Skills API operations (nested under 'skills' property)
 */
export interface SkillsAPI {
  skills: {
    list: (projectPath?: string) => Promise<Skill[]>;
    install: (skillPath: string) => Promise<IPCResult<SkillInstallOutput>>;
    remove: (skillPath: string) => Promise<IPCResult<void>>;
    getContent: (skillPath: string) => Promise<IPCResult<SkillContent>>;
  };
}

/**
 * Creates the Skills API implementation
 */
export const createSkillsAPI = (): SkillsAPI => ({
  skills: {
    list: (projectPath?: string): Promise<Skill[]> =>
      invokeIpc(IPC_CHANNELS.SKILLS_LIST, projectPath),

    install: (skillPath: string): Promise<IPCResult<SkillInstallOutput>> =>
      invokeIpc(IPC_CHANNELS.SKILLS_INSTALL, skillPath),

    remove: (skillPath: string): Promise<IPCResult<void>> =>
      invokeIpc(IPC_CHANNELS.SKILLS_REMOVE, skillPath),

    getContent: (skillPath: string): Promise<IPCResult<SkillContent>> =>
      invokeIpc(IPC_CHANNELS.SKILLS_GET_CONTENT, skillPath)
  }
});
