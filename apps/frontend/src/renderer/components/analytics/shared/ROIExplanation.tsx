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
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '../../ui/dialog';
import { ScrollArea } from '../../ui/scroll-area';

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
    examples: ['Lines of code generated', 'Dev hours saved', 'Files modified'],
    calculation: 'Hours × $150/hr × Quality Multiplier',
  },
  {
    id: 'decision',
    icon: Brain,
    color: 'bg-purple-500',
    examples: ['Features prioritized', 'High-impact ideas', 'Tasks accepted'],
    calculation: '$50-$250 per strategic decision',
  },
  {
    id: 'prevention',
    icon: Shield,
    color: 'bg-green-500',
    examples: ['Security issues found', 'Bugs prevented', 'Features NOT built'],
    calculation: '$300-$10,000 per issue prevented',
  },
  {
    id: 'knowledge',
    icon: Lightbulb,
    color: 'bg-yellow-500',
    examples: ['Codebase exploration', 'Insights gained', 'Research done'],
    calculation: 'Time saved × $150/hr × 0.4-0.5',
  },
];

const FEATURE_TYPES = [
  {
    id: 'ideation',
    icon: Zap,
    name: 'Ideation',
    valueTypes: ['decision', 'prevention', 'knowledge'],
    description: 'Generates ideas for improvements, security, performance, etc.',
    roiFactors: [
      'High-impact ideas: $50-$250 each (×5 for security)',
      'Prevention: $1,000+ per security issue found',
      'Knowledge: 1 hour brainstorming time saved',
    ],
  },
  {
    id: 'roadmap',
    icon: Sparkles,
    name: 'Roadmap',
    valueTypes: ['decision', 'prevention', 'knowledge'],
    description: 'Strategic planning and feature prioritization.',
    roiFactors: [
      'Decision: $100 per feature prioritized',
      'Prevention: 30% of avoided feature cost (~$1,500)',
      'Knowledge: 2 hours planning time saved',
    ],
  },
  {
    id: 'spec',
    icon: FileText,
    name: 'Spec Creation',
    valueTypes: ['execution', 'decision', 'prevention'],
    description: 'Requirement gathering and spec writing.',
    roiFactors: [
      'Execution: 3 hours spec writing time saved',
      'Decision: $30 per requirement clarified',
      'Prevention: $200 for first-pass success',
    ],
  },
  {
    id: 'build',
    icon: Code,
    name: 'Build (Code)',
    valueTypes: ['execution', 'prevention'],
    description: 'Code generation and implementation.',
    roiFactors: [
      'Execution: Lines ÷ 20 × $150/hr × quality',
      'Quality bonus: 1.2× for first-pass QA',
      'Prevention: $30 per file (bugs prevented)',
    ],
  },
  {
    id: 'github',
    icon: GitPullRequest,
    name: 'GitHub Automation',
    valueTypes: ['execution', 'decision', 'prevention'],
    description: 'PR review, issue triage, and automation.',
    roiFactors: [
      'PR Review: 30 min saved × $150/hr',
      'Issue Triage: 10 min saved per issue',
      'Auto-fix: $200 per issue resolved',
    ],
  },
  {
    id: 'insights',
    icon: MessageCircle,
    name: 'Insights Chat',
    valueTypes: ['knowledge', 'decision'],
    description: 'Codebase exploration and Q&A.',
    roiFactors: [
      'Knowledge: Files explored × 5 min × rate',
      'Decision: $100 per task accepted',
    ],
  },
];

const CONSTANTS = {
  hourlyRate: 150,
  timeSavings: {
    'PR Review': '30 min',
    'Issue Triage': '10 min',
    'Idea Generation': '60 min',
    'Roadmap Planning': '120 min',
    'Spec Writing': '180 min',
    'Codebase Exploration': '45 min',
  },
  preventionValues: {
    'Security (Critical)': '$10,000',
    'Security (High)': '$5,000',
    'Security (Medium)': '$1,000',
    'Performance (Critical)': '$5,000',
    'Bug (Critical)': '$3,000',
    'Bug (High)': '$1,000',
    'Bug (Medium)': '$300',
  },
};

export function ROIExplanation({ isOpen, onClose }: ROIExplanationProps) {
  const { t } = useTranslation(['analytics']);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    valueTypes: true,
    features: false,
    constants: false,
    formula: false,
  });

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
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

        <ScrollArea className="flex-1 pr-4">
          <div className="space-y-6 pb-4">
            {/* Introduction */}
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
              <p className="text-sm text-gray-700 dark:text-gray-300">
                Value is estimated based on developer time saved, issues prevented, and strategic decisions made.
              </p>
            </div>

            {/* Value Types Section */}
            <section>
              <button
                type="button"
                onClick={() => toggleSection('valueTypes')}
                className="w-full flex items-center justify-between py-2 text-left"
              >
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  {t('roiExplanation.valueTypes.title', '4 Types of Value')}
                </h3>
                {expandedSections.valueTypes ? (
                  <ChevronUp className="h-5 w-5 text-gray-500" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-gray-500" />
                )}
              </button>

              {expandedSections.valueTypes && (
                <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                  {VALUE_TYPES.map((vt) => {
                    const Icon = vt.icon;
                    return (
                      <div
                        key={vt.id}
                        className="border border-gray-200 dark:border-gray-700 rounded-lg p-4"
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <div className={`p-1.5 rounded ${vt.color}`}>
                            <Icon className="h-4 w-4 text-white" />
                          </div>
                          <h4 className="font-medium text-gray-900 dark:text-gray-100 capitalize">
                            {t(`roiExplanation.valueTypes.${vt.id}.name`, vt.id)}
                          </h4>
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                          {t(`roiExplanation.valueTypes.${vt.id}.desc`, vt.calculation)}
                        </p>
                        <ul className="text-xs text-gray-600 dark:text-gray-300 space-y-1">
                          {vt.examples.map((ex, i) => (
                            <li key={i} className="flex items-center gap-1">
                              <span className="text-gray-400">•</span> {ex}
                            </li>
                          ))}
                        </ul>
                      </div>
                    );
                  })}
                </div>
              )}
            </section>

            {/* Feature Types Section */}
            <section>
              <button
                type="button"
                onClick={() => toggleSection('features')}
                className="w-full flex items-center justify-between py-2 text-left"
              >
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  {t('roiExplanation.features.title', 'ROI by Feature Type')}
                </h3>
                {expandedSections.features ? (
                  <ChevronUp className="h-5 w-5 text-gray-500" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-gray-500" />
                )}
              </button>

              {expandedSections.features && (
                <div className="mt-4 space-y-4">
                  {FEATURE_TYPES.map((ft) => {
                    const Icon = ft.icon;
                    return (
                      <div
                        key={ft.id}
                        className="border border-gray-200 dark:border-gray-700 rounded-lg p-4"
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <Icon className="h-5 w-5 text-gray-600 dark:text-gray-400" />
                          <h4 className="font-medium text-gray-900 dark:text-gray-100">
                            {ft.name}
                          </h4>
                          <div className="flex gap-1 ml-auto">
                            {ft.valueTypes.map((vt) => {
                              const vtInfo = VALUE_TYPES.find((v) => v.id === vt);
                              return vtInfo ? (
                                <span
                                  key={vt}
                                  className={`text-xs px-1.5 py-0.5 rounded text-white ${vtInfo.color}`}
                                >
                                  {vt[0].toUpperCase()}
                                </span>
                              ) : null;
                            })}
                          </div>
                        </div>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                          {ft.description}
                        </p>
                        <ul className="text-xs text-gray-700 dark:text-gray-300 space-y-1 bg-gray-50 dark:bg-gray-900/50 rounded p-2">
                          {ft.roiFactors.map((factor, i) => (
                            <li key={i}>• {factor}</li>
                          ))}
                        </ul>
                      </div>
                    );
                  })}
                </div>
              )}
            </section>

            {/* Constants Section */}
            <section>
              <button
                type="button"
                onClick={() => toggleSection('constants')}
                className="w-full flex items-center justify-between py-2 text-left"
              >
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  {t('roiExplanation.constants.title', 'Calculation Constants')}
                </h3>
                {expandedSections.constants ? (
                  <ChevronUp className="h-5 w-5 text-gray-500" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-gray-500" />
                )}
              </button>

              {expandedSections.constants && (
                <div className="mt-4 space-y-4">
                  <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-2">
                      Developer Hourly Rate
                    </h4>
                    <p className="text-2xl font-bold text-green-600">${CONSTANTS.hourlyRate}/hr</p>
                    <p className="text-xs text-gray-500 mt-1">
                      Used for all time-based value calculations
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                      <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-3">
                        Time Savings
                      </h4>
                      <div className="space-y-2 text-sm">
                        {Object.entries(CONSTANTS.timeSavings).map(([task, time]) => (
                          <div key={task} className="flex justify-between">
                            <span className="text-gray-600 dark:text-gray-400">{task}</span>
                            <span className="font-medium text-gray-900 dark:text-gray-100">{time}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                      <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-3">
                        Prevention Values
                      </h4>
                      <div className="space-y-2 text-sm">
                        {Object.entries(CONSTANTS.preventionValues).map(([issue, value]) => (
                          <div key={issue} className="flex justify-between">
                            <span className="text-gray-600 dark:text-gray-400">{issue}</span>
                            <span className="font-medium text-green-600">{value}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </section>

            {/* Formula Section */}
            <section>
              <button
                type="button"
                onClick={() => toggleSection('formula')}
                className="w-full flex items-center justify-between py-2 text-left"
              >
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  {t('roiExplanation.formula.title', 'ROI Formula')}
                </h3>
                {expandedSections.formula ? (
                  <ChevronUp className="h-5 w-5 text-gray-500" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-gray-500" />
                )}
              </button>

              {expandedSections.formula && (
                <div className="mt-4 bg-gray-900 dark:bg-gray-950 rounded-lg p-6 text-center">
                  <div className="text-white font-mono text-lg mb-4">
                    <span className="text-blue-400">ROI</span> = (
                    <span className="text-green-400">Total Value</span> -{' '}
                    <span className="text-red-400">AI Cost</span>) /{' '}
                    <span className="text-red-400">AI Cost</span> × 100%
                  </div>
                  <div className="text-gray-400 text-sm">
                    <p className="mb-2">Where:</p>
                    <p>
                      <span className="text-green-400">Total Value</span> = Execution + Decision +
                      Prevention + Knowledge
                    </p>
                    <p>
                      <span className="text-red-400">AI Cost</span> = Token usage × Claude API pricing
                    </p>
                  </div>
                </div>
              )}
            </section>

            {/* Footer note */}
            <div className="text-xs text-gray-500 dark:text-gray-400 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-3">
              <strong>Note:</strong> ROI calculations are estimates based on industry benchmarks.
              Actual value may vary. Confidence scores (0.5-0.85) indicate estimation reliability.
            </div>
          </div>
        </ScrollArea>
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
