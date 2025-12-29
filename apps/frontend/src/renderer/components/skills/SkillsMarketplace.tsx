import { useState, useMemo } from 'react'
import { Download, Check, Search, Loader2 } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '../ui/dialog'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Badge } from '../ui/badge'
import { MARKETPLACE_CATEGORIES, type MarketplaceSkill } from './marketplace-data'
import type { Skill } from '../../../shared/types'

interface SkillsMarketplaceProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onInstall: (skillPath: string) => Promise<void>
  installedSkills: Skill[]
}

/**
 * SkillsMarketplace component provides a browsable marketplace of available skills.
 * Features:
 * - Search skills by name or description
 * - Filter by category
 * - Install skills with one click
 * - Shows installed state for already-installed skills
 */
export function SkillsMarketplace({
  open,
  onOpenChange,
  onInstall,
  installedSkills
}: SkillsMarketplaceProps) {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [installing, setInstalling] = useState<string | null>(null)

  // Flatten all skills from categories and mark installed skills
  const allSkills = useMemo(() => {
    return MARKETPLACE_CATEGORIES.flatMap(cat =>
      cat.skills.map(skill => ({
        ...skill,
        installed: installedSkills.some(is => is.name === skill.name)
      }))
    )
  }, [installedSkills])

  // Filter skills by search query and selected category
  const filteredSkills = useMemo(() => {
    return allSkills.filter(skill => {
      const matchesSearch =
        skill.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        skill.description.toLowerCase().includes(searchQuery.toLowerCase())
      const matchesCategory = !selectedCategory || skill.category === selectedCategory
      return matchesSearch && matchesCategory
    })
  }, [allSkills, searchQuery, selectedCategory])

  const handleInstall = async (skillPath: string) => {
    try {
      setInstalling(skillPath)
      await onInstall(skillPath)
    } finally {
      setInstalling(null)
    }
  }

  // Calculate total skill count across all categories
  const totalSkillCount = MARKETPLACE_CATEGORIES.reduce((sum, cat) => sum + cat.count, 0)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[900px] max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Skills Marketplace</DialogTitle>
          <DialogDescription>
            Browse and install available skills from the marketplace
          </DialogDescription>
        </DialogHeader>

        {/* Search & Filters */}
        <div className="space-y-4 mt-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder={`Search ${totalSkillCount}+ skills...`}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <div className="flex gap-2 flex-wrap">
            <Badge
              variant={!selectedCategory ? 'default' : 'outline'}
              className="cursor-pointer"
              onClick={() => setSelectedCategory(null)}
            >
              All ({allSkills.length})
            </Badge>
            {MARKETPLACE_CATEGORIES.map(cat => (
              <Badge
                key={cat.name}
                variant={selectedCategory === cat.name ? 'default' : 'outline'}
                className="cursor-pointer"
                onClick={() => setSelectedCategory(cat.name)}
              >
                {cat.displayName} ({cat.count})
              </Badge>
            ))}
          </div>
        </div>

        {/* Skills Grid */}
        <div className="flex-1 min-h-0 overflow-auto mt-4 -mx-6 px-6">
          {filteredSkills.length === 0 ? (
            <div className="flex items-center justify-center py-12 text-center text-muted-foreground">
              <div>
                <p className="text-lg font-medium mb-2">No skills found</p>
                <p className="text-sm">Try adjusting your search or filters</p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pb-4">
              {filteredSkills.map((skill) => (
                <div key={skill.path} className="border rounded-lg p-4 bg-card hover:border-primary transition-colors">
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-semibold text-sm flex-1 pr-2">{skill.name}</h3>
                    <Badge variant="secondary" className="text-xs flex-shrink-0">
                      {MARKETPLACE_CATEGORIES.find(c => c.name === skill.category)?.displayName}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground mb-4 line-clamp-3">
                    {skill.description}
                  </p>
                  <Button
                    size="sm"
                    className="w-full"
                    disabled={skill.installed || installing === skill.path}
                    onClick={() => handleInstall(skill.path)}
                    variant={skill.installed ? 'outline' : 'default'}
                  >
                    {installing === skill.path ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Installing...
                      </>
                    ) : skill.installed ? (
                      <>
                        <Check className="h-4 w-4 mr-2" />
                        Installed
                      </>
                    ) : (
                      <>
                        <Download className="h-4 w-4 mr-2" />
                        Install
                      </>
                    )}
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
