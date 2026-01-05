import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  HelpCircle,
  Zap,
  Brain,
  Shield,
  Lightbulb,
  Code,
  GitPullRequest,
  FileText,
  Sparkles,
  MessageCircle,
  GitMerge,
  ChevronDown,
  ChevronUp,
  Calculator,
  Star,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '../../ui/dialog';

interface ROIExplanationProps {
  isOpen: boolean;
  onClose: () => void;
}

// ROI calculation constants (mirrored from backend for documentation)
const VALUE_TYPES = [
  {
    id: 'execution',
    icon: Code,
    color: 'bg-blue-500',
  },
  {
    id: 'decision',
    icon: Brain,
    color: 'bg-purple-500',
  },
  {
    id: 'prevention',
    icon: Shield,
    color: 'bg-green-500',
  },
  {
    id: 'knowledge',
    icon: Lightbulb,
    color: 'bg-yellow-500',
  },
];

const FEATURE_TYPES = [
  { id: 'ideation', icon: Zap, valueTypes: ['decision', 'prevention', 'knowledge'] },
  { id: 'roadmap', icon: Sparkles, valueTypes: ['decision', 'prevention', 'knowledge'] },
  { id: 'spec', icon: FileText, valueTypes: ['execution', 'decision', 'prevention'] },
  { id: 'build', icon: Code, valueTypes: ['execution', 'prevention'] },
  { id: 'github', icon: GitPullRequest, valueTypes: ['execution', 'decision', 'prevention'] },
  { id: 'insights', icon: MessageCircle, valueTypes: ['knowledge', 'decision'] },
  { id: 'merge', icon: GitMerge, valueTypes: ['execution', 'decision', 'prevention'] },
];

const CONSTANTS = {
  hourlyRate: 150,
  timeSavings: {
    'prReview': '30 min',
    'issueTriage': '10 min',
    'ideaGeneration': '60 min',
    'roadmapPlanning': '120 min',
    'specWriting': '180 min',
    'codebaseExploration': '45 min',
    'conflictResolution': '20 min',
  },
  preventionValues: {
    'securityCritical': '$10,000',
    'securityHigh': '$5,000',
    'securityMedium': '$1,000',
    'performanceCritical': '$5,000',
    'bugCritical': '$3,000',
    'bugHigh': '$1,000',
    'bugMedium': '$300',
  },
  qualityMultipliers: {
    'qaFirstPass': '+30%',
    'qaFailed': '-30%',
    'hasTests': '+10%',
    'hasDocs': '+5%',
    'hasTypes': '+5%',
    'highCoverage': '+10%',
    'lintErrors': '-5%',
    'reworkNeeded': '-20%',
  },
};

export function ROIExplanation({ isOpen, onClose }: ROIExplanationProps) {
  const { t } = useTranslation(['analytics']);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    formula: true,
    valueTypes: false,
    qualityMultiplier: false,
    features: false,
    constants: false,
    confidence: false,
  });

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-3xl h-[85vh] flex flex-col p-0">
        <DialogHeader className="px-6 pt-6 pb-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
          <DialogTitle className="flex items-center gap-3">
            <HelpCircle className="h-6 w-6 text-blue-500" />
            {t('roiExplanation.title', 'How ROI is Calculated')}
          </DialogTitle>
          <DialogDescription>
            {t('roiExplanation.intro',
              'Auto-Claude calculates ROI by measuring the value generated across 4 dimensions, compared to the AI cost.'
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto px-6 py-4">
          <div className="space-y-4 pb-6">
            {/* Formula Section - Open by default */}
            <section className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
              <button
                type="button"
                onClick={() => toggleSection('formula')}
                className="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 text-left hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <div className="flex items-center gap-2">
                  <Calculator className="h-5 w-5 text-blue-500" />
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                    {t('roiExplanation.formula.title', 'ROI Formula')}
                  </h3>
                </div>
                {expandedSections.formula ? (
                  <ChevronUp className="h-5 w-5 text-gray-500" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-gray-500" />
                )}
              </button>

              {expandedSections.formula && (
                <div className="p-4 bg-gray-900 dark:bg-gray-950">
                  <div className="text-white font-mono text-lg mb-4 text-center">
                    <span className="text-blue-400">ROI</span> = (
                    <span className="text-green-400">{t('roiExplanation.formula.totalValue', 'Total Value')}</span> -{' '}
                    <span className="text-red-400">{t('roiExplanation.formula.aiCost', 'AI Cost')}</span>) /{' '}
                    <span className="text-red-400">{t('roiExplanation.formula.aiCost', 'AI Cost')}</span> × 100%
                  </div>
                  <div className="text-gray-400 text-sm text-center space-y-1">
                    <p>
                      <span className="text-green-400">{t('roiExplanation.formula.totalValue', 'Total Value')}</span> = Execution + Decision + Prevention + Knowledge
                    </p>
                    <p>
                      <span className="text-red-400">{t('roiExplanation.formula.aiCost', 'AI Cost')}</span> = {t('roiExplanation.formula.aiCost', 'Tokens used × Claude API pricing')}
                    </p>
                  </div>
                </div>
              )}
            </section>

            {/* Value Types Section */}
            <section className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
              <button
                type="button"
                onClick={() => toggleSection('valueTypes')}
                className="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 text-left hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <div className="flex items-center gap-2">
                  <div className="flex -space-x-1">
                    <div className="w-4 h-4 rounded-full bg-blue-500" />
                    <div className="w-4 h-4 rounded-full bg-purple-500" />
                    <div className="w-4 h-4 rounded-full bg-green-500" />
                    <div className="w-4 h-4 rounded-full bg-yellow-500" />
                  </div>
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                    {t('roiExplanation.valueTypes.title', '4 Types of Value')}
                  </h3>
                </div>
                {expandedSections.valueTypes ? (
                  <ChevronUp className="h-5 w-5 text-gray-500" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-gray-500" />
                )}
              </button>

              {expandedSections.valueTypes && (
                <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-3">
                  {VALUE_TYPES.map((vt) => {
                    const Icon = vt.icon;
                    const examples = t(`roiExplanation.valueTypes.${vt.id}.examples`, { returnObjects: true }) as string[];
                    return (
                      <div
                        key={vt.id}
                        className="border border-gray-200 dark:border-gray-700 rounded-lg p-3"
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <div className={`p-1.5 rounded ${vt.color}`}>
                            <Icon className="h-4 w-4 text-white" />
                          </div>
                          <h4 className="font-medium text-gray-900 dark:text-gray-100">
                            {t(`roiExplanation.valueTypes.${vt.id}.name`, vt.id)}
                          </h4>
                        </div>
                        <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">
                          {t(`roiExplanation.valueTypes.${vt.id}.desc`)}
                        </p>
                        <p className="text-xs text-blue-600 dark:text-blue-400 font-mono mb-2">
                          {t(`roiExplanation.valueTypes.${vt.id}.calculation`)}
                        </p>
                        {Array.isArray(examples) && (
                          <ul className="text-xs text-gray-500 dark:text-gray-400 space-y-0.5">
                            {examples.map((ex, i) => (
                              <li key={i}>• {ex}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </section>

            {/* Quality Multiplier Section */}
            <section className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
              <button
                type="button"
                onClick={() => toggleSection('qualityMultiplier')}
                className="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 text-left hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <div className="flex items-center gap-2">
                  <Star className="h-5 w-5 text-yellow-500" />
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                    {t('roiExplanation.qualityMultiplier.title', 'Quality Multiplier')}
                  </h3>
                </div>
                {expandedSections.qualityMultiplier ? (
                  <ChevronUp className="h-5 w-5 text-gray-500" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-gray-500" />
                )}
              </button>

              {expandedSections.qualityMultiplier && (
                <div className="p-4">
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                    {t('roiExplanation.qualityMultiplier.description', 'Build ROI is adjusted based on code quality indicators:')}
                  </p>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    {Object.entries(CONSTANTS.qualityMultipliers).map(([key, value]) => (
                      <div key={key} className="flex justify-between items-center p-2 bg-gray-50 dark:bg-gray-800 rounded">
                        <span className="text-gray-600 dark:text-gray-400 text-xs">
                          {t(`roiExplanation.qualityMultiplier.factors.${key}`, key)}
                        </span>
                        <span className={`font-mono text-xs ${value.startsWith('+') ? 'text-green-600' : 'text-red-600'}`}>
                          {value}
                        </span>
                      </div>
                    ))}
                  </div>
                  <p className="text-xs text-gray-500 mt-3 text-center">
                    {t('roiExplanation.qualityMultiplier.range', 'Final multiplier ranges from 0.5× to 1.5×')}
                  </p>
                </div>
              )}
            </section>

            {/* Feature Types Section */}
            <section className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
              <button
                type="button"
                onClick={() => toggleSection('features')}
                className="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 text-left hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <div className="flex items-center gap-2">
                  <Code className="h-5 w-5 text-indigo-500" />
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                    {t('roiExplanation.features.title', 'ROI by Feature Type')}
                  </h3>
                </div>
                {expandedSections.features ? (
                  <ChevronUp className="h-5 w-5 text-gray-500" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-gray-500" />
                )}
              </button>

              {expandedSections.features && (
                <div className="p-4 space-y-3">
                  {FEATURE_TYPES.map((ft) => {
                    const Icon = ft.icon;
                    const factors = t(`roiExplanation.features.${ft.id}.factors`, { returnObjects: true }) as string[];
                    return (
                      <div
                        key={ft.id}
                        className="border border-gray-200 dark:border-gray-700 rounded-lg p-3"
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <Icon className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                          <h4 className="font-medium text-gray-900 dark:text-gray-100 text-sm">
                            {t(`roiExplanation.features.${ft.id}.name`, ft.id)}
                          </h4>
                          <div className="flex gap-1 ml-auto">
                            {ft.valueTypes.map((vt) => {
                              const vtInfo = VALUE_TYPES.find((v) => v.id === vt);
                              return vtInfo ? (
                                <span
                                  key={vt}
                                  className={`text-[10px] px-1.5 py-0.5 rounded text-white ${vtInfo.color}`}
                                >
                                  {vt[0].toUpperCase()}
                                </span>
                              ) : null;
                            })}
                          </div>
                        </div>
                        {Array.isArray(factors) && (
                          <ul className="text-xs text-gray-600 dark:text-gray-300 space-y-0.5 bg-gray-50 dark:bg-gray-900/50 rounded p-2">
                            {factors.map((factor, i) => (
                              <li key={i}>• {factor}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </section>

            {/* Constants Section */}
            <section className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
              <button
                type="button"
                onClick={() => toggleSection('constants')}
                className="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 text-left hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <div className="flex items-center gap-2">
                  <span className="text-lg">📊</span>
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                    {t('roiExplanation.constants.title', 'Default Constants')}
                  </h3>
                </div>
                {expandedSections.constants ? (
                  <ChevronUp className="h-5 w-5 text-gray-500" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-gray-500" />
                )}
              </button>

              {expandedSections.constants && (
                <div className="p-4 space-y-4">
                  <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3 text-center">
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {t('roiExplanation.constants.hourlyRate', 'Developer Hourly Rate: $150/hr (configurable)')}
                    </p>
                    <p className="text-2xl font-bold text-green-600">${CONSTANTS.hourlyRate}/hr</p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-3">
                      <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-2 text-sm">
                        {t('roiExplanation.constants.timeSavings.title', 'Time Savings Estimates')}
                      </h4>
                      <div className="space-y-1.5 text-xs">
                        {Object.entries(CONSTANTS.timeSavings).map(([key, time]) => (
                          <div key={key} className="flex justify-between">
                            <span className="text-gray-600 dark:text-gray-400">
                              {t(`roiExplanation.constants.timeSavings.${key}`, key)}
                            </span>
                            <span className="font-medium text-gray-900 dark:text-gray-100">{time}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-3">
                      <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-2 text-sm">
                        {t('roiExplanation.constants.preventionValues.title', 'Issue Prevention Values')}
                      </h4>
                      <div className="space-y-1.5 text-xs">
                        {Object.entries(CONSTANTS.preventionValues).map(([key, value]) => (
                          <div key={key} className="flex justify-between">
                            <span className="text-gray-600 dark:text-gray-400">
                              {t(`roiExplanation.constants.preventionValues.${key}`, key)}
                            </span>
                            <span className="font-medium text-green-600">{value}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </section>

            {/* Confidence Section */}
            <section className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
              <button
                type="button"
                onClick={() => toggleSection('confidence')}
                className="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 text-left hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <div className="flex items-center gap-2">
                  <span className="text-lg">🎯</span>
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                    {t('roiExplanation.confidence.title', 'Confidence Scores')}
                  </h3>
                </div>
                {expandedSections.confidence ? (
                  <ChevronUp className="h-5 w-5 text-gray-500" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-gray-500" />
                )}
              </button>

              {expandedSections.confidence && (
                <div className="p-4">
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                    {t('roiExplanation.confidence.description', 'Each ROI calculation includes a confidence score (0.5-0.85) indicating estimation reliability:')}
                  </p>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center gap-2 p-2 bg-green-50 dark:bg-green-900/20 rounded">
                      <div className="w-2 h-2 rounded-full bg-green-500" />
                      <span className="text-gray-700 dark:text-gray-300">{t('roiExplanation.confidence.high', '0.85: Build with QA passed (measurable outcomes)')}</span>
                    </div>
                    <div className="flex items-center gap-2 p-2 bg-yellow-50 dark:bg-yellow-900/20 rounded">
                      <div className="w-2 h-2 rounded-full bg-yellow-500" />
                      <span className="text-gray-700 dark:text-gray-300">{t('roiExplanation.confidence.medium', '0.75: Spec creation, Merge resolution')}</span>
                    </div>
                    <div className="flex items-center gap-2 p-2 bg-orange-50 dark:bg-orange-900/20 rounded">
                      <div className="w-2 h-2 rounded-full bg-orange-500" />
                      <span className="text-gray-700 dark:text-gray-300">{t('roiExplanation.confidence.low', '0.60: Roadmap, Insights (strategic estimates)')}</span>
                    </div>
                  </div>
                </div>
              )}
            </section>

            {/* Footer note */}
            <div className="text-xs text-gray-500 dark:text-gray-400 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-3">
              <strong>⚠️</strong> {t('roiExplanation.note', 'ROI calculations are estimates based on industry benchmarks. Actual value may vary based on project complexity, team size, and developer experience.')}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// Button component to open the explanation
export function ROIExplanationButton({ onClick }: { onClick: () => void }) {
  const { t } = useTranslation(['analytics']);

  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
    >
      <HelpCircle className="h-4 w-4" />
      <span>{t('roiExplanation.button', 'How is ROI calculated?')}</span>
    </button>
  );
}

export default ROIExplanation;
