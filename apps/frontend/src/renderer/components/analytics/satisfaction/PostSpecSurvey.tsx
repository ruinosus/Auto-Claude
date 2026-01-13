/**
 * Post-Spec Survey
 * =================
 *
 * Modal dialog for collecting user feedback after spec completion.
 * Collects ratings for satisfaction, quality, time saved, and NPS.
 *
 * Now uses ROI Engine API via the API Bridge for survey submission.
 */

import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../../ui/dialog';
import { Button } from '../../ui/button';
import { Textarea } from '../../ui/textarea';
import { Label } from '../../ui/label';
import { Star } from 'lucide-react';
import { apiBridge } from '../../../services/api-bridge';
import { useProjectPath } from '../../../hooks/useProjectPath';

interface StarRatingProps {
  value: number;
  onChange: (value: number) => void;
  label: string;
  description?: string;
}

function StarRating({ value, onChange, label, description }: StarRatingProps) {
  const [hoverValue, setHoverValue] = useState<number | null>(null);

  return (
    <div className="space-y-2">
      <Label className="text-sm font-medium">{label}</Label>
      {description && <p className="text-xs text-muted-foreground">{description}</p>}
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            className="p-1 hover:scale-110 transition-transform focus:outline-none focus:ring-2 focus:ring-primary rounded"
            onClick={() => onChange(star)}
            onMouseEnter={() => setHoverValue(star)}
            onMouseLeave={() => setHoverValue(null)}
            aria-label={`Rate ${star} out of 5`}
          >
            <Star
              className={`h-8 w-8 transition-colors ${
                star <= (hoverValue ?? value)
                  ? 'fill-yellow-400 text-yellow-400'
                  : 'text-muted-foreground'
              }`}
            />
          </button>
        ))}
      </div>
    </div>
  );
}

interface SurveyFormData {
  overallSatisfaction: number;
  outputQuality: number;
  timeSavedPerception: number;
  wouldRecommend: number;
  feedback: string;
  improvementSuggestions: string;
}

interface PostSpecSurveyProps {
  isOpen: boolean;
  onClose: () => void;
  specId: string;
  userId?: string;
  onSubmitSuccess?: () => void;
}

export function PostSpecSurvey({
  isOpen,
  onClose,
  specId,
  userId = 'anonymous',
  onSubmitSuccess,
}: PostSpecSurveyProps) {
  const { t } = useTranslation(['analytics', 'common']);
  const { projectPath } = useProjectPath();

  const [formData, setFormData] = useState<SurveyFormData>({
    overallSatisfaction: 0,
    outputQuality: 0,
    timeSavedPerception: 0,
    wouldRecommend: 0,
    feedback: '',
    improvementSuggestions: '',
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRatingChange = useCallback((field: keyof SurveyFormData, value: number) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  }, []);

  const handleTextChange = useCallback((field: keyof SurveyFormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  }, []);

  const isValid = formData.overallSatisfaction > 0 &&
    formData.outputQuality > 0 &&
    formData.timeSavedPerception > 0 &&
    formData.wouldRecommend > 0;

  const handleSubmit = async () => {
    if (!isValid || !projectPath) return;

    setIsSubmitting(true);
    setError(null);

    try {
      // Use API Bridge - routes to ROI Engine for survey submission
      const context = apiBridge.createContext(projectPath);
      await apiBridge.satisfaction.submitSurvey(context, {
        spec_id: specId,
        user_id: userId,
        overall_satisfaction: formData.overallSatisfaction,
        output_quality: formData.outputQuality,
        time_saved_perception: formData.timeSavedPerception,
        would_recommend: formData.wouldRecommend,
        feedback: formData.feedback || undefined,
        improvement_suggestions: formData.improvementSuggestions || undefined,
      });

      onSubmitSuccess?.();
      onClose();

      // Reset form
      setFormData({
        overallSatisfaction: 0,
        outputQuality: 0,
        timeSavedPerception: 0,
        wouldRecommend: 0,
        feedback: '',
        improvementSuggestions: '',
      });
    } catch (err) {
      console.error('Failed to submit survey:', err);
      setError(t('analytics:satisfaction.survey.submitError'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSkip = () => {
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{t('analytics:satisfaction.survey.title')}</DialogTitle>
          <DialogDescription>
            {t('analytics:satisfaction.survey.description', { specId })}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Overall Satisfaction */}
          <StarRating
            value={formData.overallSatisfaction}
            onChange={(value) => handleRatingChange('overallSatisfaction', value)}
            label={t('analytics:satisfaction.survey.questions.overall')}
          />

          {/* Output Quality */}
          <StarRating
            value={formData.outputQuality}
            onChange={(value) => handleRatingChange('outputQuality', value)}
            label={t('analytics:satisfaction.survey.questions.quality')}
          />

          {/* Time Saved */}
          <StarRating
            value={formData.timeSavedPerception}
            onChange={(value) => handleRatingChange('timeSavedPerception', value)}
            label={t('analytics:satisfaction.survey.questions.timeSaved')}
          />

          {/* Would Recommend (NPS) */}
          <StarRating
            value={formData.wouldRecommend}
            onChange={(value) => handleRatingChange('wouldRecommend', value)}
            label={t('analytics:satisfaction.survey.questions.recommend')}
            description={t('analytics:satisfaction.survey.questions.recommendHint')}
          />

          {/* Feedback */}
          <div className="space-y-2">
            <Label htmlFor="feedback">{t('analytics:satisfaction.survey.questions.feedback')}</Label>
            <Textarea
              id="feedback"
              placeholder={t('analytics:satisfaction.survey.questions.feedbackPlaceholder')}
              value={formData.feedback}
              onChange={(e) => handleTextChange('feedback', e.target.value)}
              rows={2}
            />
          </div>

          {/* Improvement Suggestions */}
          <div className="space-y-2">
            <Label htmlFor="improvements">
              {t('analytics:satisfaction.survey.questions.improvements')}
            </Label>
            <Textarea
              id="improvements"
              placeholder={t('analytics:satisfaction.survey.questions.improvementsPlaceholder')}
              value={formData.improvementSuggestions}
              onChange={(e) => handleTextChange('improvementSuggestions', e.target.value)}
              rows={2}
            />
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="ghost" onClick={handleSkip} disabled={isSubmitting}>
            {t('analytics:satisfaction.survey.skip')}
          </Button>
          <Button onClick={handleSubmit} disabled={!isValid || isSubmitting}>
            {isSubmitting
              ? t('analytics:satisfaction.survey.submitting')
              : t('analytics:satisfaction.survey.submit')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default PostSpecSurvey;
