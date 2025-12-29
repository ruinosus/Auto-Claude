import { useState, useEffect, useCallback } from 'react'
import { Package, Loader2, AlertCircle, X } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '../ui/dialog'
import { Badge } from '../ui/badge'
import { ScrollArea } from '../ui/scroll-area'
import { Button } from '../ui/button'
import type { Skill } from '../../../shared/types'

interface SkillPreviewProps {
  skill: Skill
  open: boolean
  onOpenChange: (open: boolean) => void
}

/**
 * SkillPreview component displays a dialog with the full content of a skill.
 * Loads skill content from the file system when the dialog is opened.
 */
export function SkillPreview({ skill, open, onOpenChange }: SkillPreviewProps) {
  const [content, setContent] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadContent = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const result = await window.electronAPI.skills.getContent(skill.path)

      if (result.success && result.data) {
        setContent(result.data.content)
      } else {
        setError(result.error || 'Failed to load skill content')
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err)
      setError(`Error loading skill content: ${errorMessage}`)
    } finally {
      setLoading(false)
    }
  }, [skill.path])

  useEffect(() => {
    if (open) {
      loadContent()
    }
  }, [open, loadContent])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl h-[85vh] flex flex-col p-0" hideCloseButton>
        <div className="flex items-start justify-between px-6 pt-6 pb-4 border-b shrink-0">
          <div className="flex-1 min-w-0">
            <DialogHeader className="space-y-0">
              <DialogTitle className="flex items-center gap-3">
                <Package className="h-5 w-5 text-primary" />
                <span>{skill.name}</span>
              </DialogTitle>
              <DialogDescription className="sr-only">
                Skill content preview for {skill.name}
              </DialogDescription>
            </DialogHeader>
            <div className="flex flex-wrap gap-2 mt-3">
              <Badge variant={skill.source === 'user' ? 'default' : 'secondary'}>
                {skill.source}
              </Badge>
              {skill.category && (
                <Badge variant="outline">{skill.category}</Badge>
              )}
              {skill.version && (
                <Badge variant="outline">v{skill.version}</Badge>
              )}
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="shrink-0 ml-4"
            onClick={() => onOpenChange(false)}
          >
            <X className="h-4 w-4" />
            <span className="sr-only">Close</span>
          </Button>
        </div>

        <div className="flex-1 min-h-0 overflow-auto">
          <div className="px-6 py-4 pb-8">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                <span className="ml-3 text-muted-foreground">Loading skill content...</span>
              </div>
            ) : error ? (
              <div className="flex items-center justify-center py-12 text-destructive">
                <AlertCircle className="h-5 w-5 mr-2" />
                <span>{error}</span>
              </div>
            ) : (
              <pre className="whitespace-pre-wrap font-mono text-sm bg-muted/50 p-4 rounded-lg">
                {content}
              </pre>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
