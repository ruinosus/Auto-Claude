import { Eye, Trash2, Package } from 'lucide-react'
import { Button } from '../ui/button'
import { Badge } from '../ui/badge'
import type { Skill } from '../../../shared/types'

interface SkillCardProps {
  skill: Skill
  onPreview: () => void
  onRemove: () => void
}

export function SkillCard({ skill, onPreview, onRemove }: SkillCardProps) {
  return (
    <div className="border rounded-lg p-4 hover:border-primary transition-colors bg-card">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <Package className="h-5 w-5 text-primary flex-shrink-0" />
          <h3 className="font-semibold text-sm">{skill.name}</h3>
        </div>
        <Badge
          variant={skill.source === 'user' ? 'default' : 'secondary'}
          className="text-xs"
        >
          {skill.source}
        </Badge>
      </div>

      {skill.category && (
        <Badge variant="outline" className="text-xs mb-2">
          {skill.category}
        </Badge>
      )}

      <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
        {skill.description}
      </p>

      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={onPreview}
          className="flex-1"
        >
          <Eye className="h-4 w-4 mr-2" />
          Preview
        </Button>
        <Button
          variant="destructive"
          size="sm"
          onClick={onRemove}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
