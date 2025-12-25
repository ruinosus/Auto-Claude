import { useState, useEffect, useCallback } from 'react'
import { Package, Download, Search, RefreshCw } from 'lucide-react'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { SkillCard } from './SkillCard'
import { SkillsMarketplace } from './SkillsMarketplace'
import { SkillPreview } from './SkillPreview'
import { useProjectStore } from '../../stores/project-store'
import type { Skill } from '../../../shared/types'

/**
 * SkillsManager is the main component for managing Claude skills.
 * It provides:
 * - List of installed skills (user and project)
 * - Search/filter functionality
 * - Skill preview modal
 * - Marketplace integration for installing new skills
 * - Remove skill functionality
 */
export function SkillsManager() {
  const [skills, setSkills] = useState<Skill[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null)
  const [showMarketplace, setShowMarketplace] = useState(false)

  // Get current project from store
  const selectedProject = useProjectStore((state) => state.getSelectedProject())

  const loadSkills = useCallback(async () => {
    try {
      setLoading(true)
      // Pass project path to list skills from both user and project locations
      const projectPath = selectedProject?.path
      const installedSkills = await window.electronAPI.skills.list(projectPath)
      setSkills(installedSkills)
    } catch (error) {
      console.error('Failed to load skills:', error)
      setSkills([])
    } finally {
      setLoading(false)
    }
  }, [selectedProject?.path])

  // Load skills on mount and when project changes
  useEffect(() => {
    loadSkills()
  }, [loadSkills])

  const handleRefresh = async () => {
    try {
      setRefreshing(true)
      await loadSkills()
    } finally {
      setRefreshing(false)
    }
  }

  const handleInstall = async (skillPath: string) => {
    try {
      const result = await window.electronAPI.skills.install(skillPath)
      if (result.success) {
        await loadSkills()
      } else {
        alert(`Failed to install skill: ${result.error || 'Unknown error'}`)
      }
    } catch (error) {
      alert(`Failed to install skill: ${error instanceof Error ? error.message : String(error)}`)
    }
  }

  const handleRemove = async (skillPath: string) => {
    if (!confirm('Are you sure you want to remove this skill?')) {
      return
    }

    try {
      const result = await window.electronAPI.skills.remove(skillPath)
      if (result.success) {
        await loadSkills()
      } else {
        alert(`Failed to remove skill: ${result.error || 'Unknown error'}`)
      }
    } catch (error) {
      alert(`Failed to remove skill: ${error instanceof Error ? error.message : String(error)}`)
    }
  }

  // Filter skills by search query
  const filteredSkills = skills.filter(skill =>
    skill.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    skill.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (skill.category && skill.category.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-2">
          <Package className="h-5 w-5" />
          <h2 className="text-lg font-semibold">Skills Manager</h2>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleRefresh}
            disabled={refreshing}
            title="Refresh skills list"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          </Button>
        </div>
        <Button onClick={() => setShowMarketplace(true)}>
          <Download className="h-4 w-4 mr-2" />
          Browse Marketplace
        </Button>
      </div>

      {/* Search */}
      <div className="p-4 border-b">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search installed skills..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      {/* Stats */}
      <div className="px-4 py-2 border-b bg-muted/50">
        <p className="text-sm text-muted-foreground">
          {skills.length} skill{skills.length !== 1 ? 's' : ''} installed
          {searchQuery && ` • ${filteredSkills.length} matching search`}
        </p>
      </div>

      {/* Skills List */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <div className="text-center py-8 text-muted-foreground">
            Loading skills...
          </div>
        ) : filteredSkills.length === 0 ? (
          <div className="text-center py-8">
            <Package className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground mb-2">
              {searchQuery ? 'No skills found matching your search' : 'No skills installed'}
            </p>
            {!searchQuery && (
              <Button onClick={() => setShowMarketplace(true)} className="mt-4">
                <Download className="h-4 w-4 mr-2" />
                Browse Marketplace
              </Button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredSkills.map((skill) => (
              <SkillCard
                key={skill.path}
                skill={skill}
                onPreview={() => setSelectedSkill(skill)}
                onRemove={() => handleRemove(skill.path)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Marketplace Modal */}
      <SkillsMarketplace
        open={showMarketplace}
        onOpenChange={setShowMarketplace}
        onInstall={handleInstall}
        installedSkills={skills}
      />

      {/* Preview Modal */}
      {selectedSkill && (
        <SkillPreview
          skill={selectedSkill}
          open={!!selectedSkill}
          onOpenChange={(open) => {
            if (!open) setSelectedSkill(null)
          }}
        />
      )}
    </div>
  )
}
