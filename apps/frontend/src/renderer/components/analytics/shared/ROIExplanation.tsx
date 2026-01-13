import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  HelpCircle,
  Boxes,
  Users,
  Calculator,
  Star,
  FileText,
  Code,
  TestTube,
  Shield,
  GitBranch,
  Layout,
  ChevronDown,
  ChevronUp,
  Package,
  Clock,
  DollarSign,
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

// Role-based valuation constants (from ROI Engine)
const ROLES = [
  {
    id: 'architect',
    icon: Layout,
    color: 'bg-purple-500',
    multiplier: 1.2,
    artifacts: ['diagram', 'architecture_insight', 'system_design', 'adr', 'api_design'],
  },
  {
    id: 'tech_lead',
    icon: GitBranch,
    color: 'bg-blue-500',
    multiplier: 1.15,
    artifacts: ['spec_document', 'implementation_plan', 'requirements', 'complexity_assessment'],
  },
  {
    id: 'developer',
    icon: Code,
    color: 'bg-green-500',
    multiplier: 1.0,
    artifacts: ['code_example', 'refactoring', 'bug_fix', 'commit', 'pr_verdict'],
  },
  {
    id: 'qa',
    icon: TestTube,
    color: 'bg-yellow-500',
    multiplier: 0.9,
    artifacts: ['test_case', 'qa_report', 'qa_verdict', 'qa_finding'],
  },
  {
    id: 'devops',
    icon: Shield,
    color: 'bg-red-500',
    multiplier: 1.1,
    artifacts: ['security_finding', 'performance_insight', 'deployment_plan'],
  },
];

// Seniority rates
const SENIORITY_RATES = {
  junior: { rate: 50, label: 'Junior' },
  mid: { rate: 75, label: 'Mid-level' },
  senior: { rate: 125, label: 'Senior' },
  staff: { rate: 175, label: 'Staff' },
  principal: { rate: 225, label: 'Principal' },
};

// Sample artifact types with estimated hours
const ARTIFACT_EXAMPLES = [
  { type: 'diagram', role: 'Architect', hours: 2.0, rate: 150, value: 300 },
  { type: 'spec_document', role: 'Tech Lead', hours: 3.0, rate: 144, value: 432 },
  { type: 'code_example', role: 'Developer', hours: 1.0, rate: 125, value: 125 },
  { type: 'test_case', role: 'QA', hours: 0.5, rate: 113, value: 56 },
  { type: 'security_finding', role: 'DevOps', hours: 1.0, rate: 138, value: 138 },
];

export function ROIExplanation({ isOpen, onClose }: ROIExplanationProps) {
  const { t } = useTranslation(['analytics']);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    formula: true,
    artifacts: false,
    roles: false,
    quality: false,
    examples: false,
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
              'Auto-Claude calculates ROI based on artifacts produced. Each artifact type maps to a squad role with an hourly rate, creating concrete value metrics.'
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
                    <span className="text-green-400">Artifact Value</span> -{' '}
                    <span className="text-red-400">Token Cost</span>) /{' '}
                    <span className="text-red-400">Token Cost</span> × 100%
                  </div>
                  <div className="text-gray-400 text-sm text-center space-y-2">
                    <p>
                      <span className="text-green-400">Artifact Value</span> = Σ (
                      <span className="text-yellow-400">Hourly Rate</span> ×{' '}
                      <span className="text-purple-400">Estimated Hours</span> ×{' '}
                      <span className="text-cyan-400">Quality Score</span>)
                    </p>
                    <p>
                      <span className="text-yellow-400">Hourly Rate</span> ={' '}
                      <span className="text-pink-400">Seniority Base</span> ×{' '}
                      <span className="text-orange-400">Role Multiplier</span>
                    </p>
                    <p className="text-xs mt-2">
                      <span className="text-red-400">Token Cost</span> = Claude API usage (tokens × pricing)
                    </p>
                  </div>
                </div>
              )}
            </section>

            {/* Artifact-Based Valuation Section */}
            <section className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
              <button
                type="button"
                onClick={() => toggleSection('artifacts')}
                className="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 text-left hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <div className="flex items-center gap-2">
                  <Boxes className="h-5 w-5 text-green-500" />
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                    {t('roiExplanation.artifacts.title', 'Artifact-Based Valuation')}
                  </h3>
                </div>
                {expandedSections.artifacts ? (
                  <ChevronUp className="h-5 w-5 text-gray-500" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-gray-500" />
                )}
              </button>

              {expandedSections.artifacts && (
                <div className="p-4 space-y-4">
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {t('roiExplanation.artifacts.description',
                      'Every output Auto-Claude produces is tracked as an artifact. Each artifact type is mapped to the squad role that would typically produce it.'
                    )}
                  </p>

                  <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
                      <Package className="h-4 w-4" />
                      {t('roiExplanation.artifacts.howItWorks', 'How It Works')}
                    </h4>
                    <ol className="text-sm text-gray-700 dark:text-gray-300 space-y-2 list-decimal list-inside">
                      <li>{t('roiExplanation.artifacts.step1', 'Agent produces an artifact (diagram, spec, code, etc.)')}</li>
                      <li>{t('roiExplanation.artifacts.step2', 'Artifact type maps to a squad role (e.g., diagram → Architect)')}</li>
                      <li>{t('roiExplanation.artifacts.step3', 'Estimated hours assigned based on artifact complexity')}</li>
                      <li>{t('roiExplanation.artifacts.step4', 'Value = Role hourly rate × Estimated hours')}</li>
                    </ol>
                  </div>

                  <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-3">
                    <p className="text-sm text-yellow-800 dark:text-yellow-200">
                      <strong>💡</strong> {t('roiExplanation.artifacts.note',
                        'Only complete artifacts count toward ROI. Draft artifacts are tracked but excluded from value calculations.'
                      )}
                    </p>
                  </div>
                </div>
              )}
            </section>

            {/* Squad Roles Section */}
            <section className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
              <button
                type="button"
                onClick={() => toggleSection('roles')}
                className="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 text-left hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <div className="flex items-center gap-2">
                  <Users className="h-5 w-5 text-purple-500" />
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                    {t('roiExplanation.roles.title', 'Squad Roles & Rates')}
                  </h3>
                </div>
                {expandedSections.roles ? (
                  <ChevronUp className="h-5 w-5 text-gray-500" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-gray-500" />
                )}
              </button>

              {expandedSections.roles && (
                <div className="p-4 space-y-4">
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                    {t('roiExplanation.roles.description',
                      'Auto-Claude simulates a software squad. Each role has a multiplier applied to the seniority base rate.'
                    )}
                  </p>

                  {/* Seniority Rates */}
                  <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
                    <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-2 text-sm flex items-center gap-2">
                      <DollarSign className="h-4 w-4" />
                      {t('roiExplanation.roles.seniorityRates', 'Seniority Base Rates')}
                    </h4>
                    <div className="grid grid-cols-5 gap-2 text-xs">
                      {Object.entries(SENIORITY_RATES).map(([key, { rate, label }]) => (
                        <div key={key} className="text-center p-2 bg-white dark:bg-gray-700 rounded">
                          <div className="font-medium text-gray-900 dark:text-gray-100">{label}</div>
                          <div className="text-green-600 font-mono">${rate}/hr</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Role Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {ROLES.map((role) => {
                      const Icon = role.icon;
                      return (
                        <div
                          key={role.id}
                          className="border border-gray-200 dark:border-gray-700 rounded-lg p-3"
                        >
                          <div className="flex items-center gap-2 mb-2">
                            <div className={`p-1.5 rounded ${role.color}`}>
                              <Icon className="h-4 w-4 text-white" />
                            </div>
                            <h4 className="font-medium text-gray-900 dark:text-gray-100 capitalize">
                              {role.id.replace('_', ' ')}
                            </h4>
                            <span className="ml-auto text-xs font-mono bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded">
                              ×{role.multiplier}
                            </span>
                          </div>
                          <div className="flex flex-wrap gap-1">
                            {role.artifacts.slice(0, 4).map((artifact) => (
                              <span
                                key={artifact}
                                className="text-[10px] px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-gray-600 dark:text-gray-300"
                              >
                                {artifact.replace('_', ' ')}
                              </span>
                            ))}
                            {role.artifacts.length > 4 && (
                              <span className="text-[10px] px-1.5 py-0.5 text-gray-500">
                                +{role.artifacts.length - 4} more
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  <p className="text-xs text-gray-500 text-center">
                    {t('roiExplanation.roles.example',
                      'Example: Senior Architect = $125 × 1.2 = $150/hr'
                    )}
                  </p>
                </div>
              )}
            </section>

            {/* Quality Adjustment Section */}
            <section className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
              <button
                type="button"
                onClick={() => toggleSection('quality')}
                className="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 text-left hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <div className="flex items-center gap-2">
                  <Star className="h-5 w-5 text-yellow-500" />
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                    {t('roiExplanation.quality.title', 'Quality Adjustment')}
                  </h3>
                </div>
                {expandedSections.quality ? (
                  <ChevronUp className="h-5 w-5 text-gray-500" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-gray-500" />
                )}
              </button>

              {expandedSections.quality && (
                <div className="p-4 space-y-4">
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {t('roiExplanation.quality.description',
                      'Each artifact has a quality score (0.0 to 1.0) that adjusts its final value. This accounts for incomplete or low-quality outputs.'
                    )}
                  </p>

                  <div className="bg-gray-900 dark:bg-gray-950 rounded-lg p-4">
                    <div className="text-white font-mono text-center mb-3">
                      <span className="text-cyan-400">Adjusted Value</span> = Base Value × (0.5 + Quality × 0.5)
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-xs text-center">
                      <div className="bg-red-900/50 rounded p-2">
                        <div className="text-red-300">Quality: 0.0</div>
                        <div className="text-white font-medium">50% value</div>
                      </div>
                      <div className="bg-yellow-900/50 rounded p-2">
                        <div className="text-yellow-300">Quality: 0.5</div>
                        <div className="text-white font-medium">75% value</div>
                      </div>
                      <div className="bg-green-900/50 rounded p-2">
                        <div className="text-green-300">Quality: 1.0</div>
                        <div className="text-white font-medium">100% value</div>
                      </div>
                    </div>
                  </div>

                  <div className="text-xs text-gray-500 space-y-1">
                    <p>• {t('roiExplanation.quality.factor1', 'Quality determined by QA feedback, code review scores, test coverage')}</p>
                    <p>• {t('roiExplanation.quality.factor2', 'Minimum 50% value ensures partial credit for incomplete work')}</p>
                    <p>• {t('roiExplanation.quality.factor3', 'Draft artifacts (status: draft) are excluded from ROI entirely')}</p>
                  </div>
                </div>
              )}
            </section>

            {/* Value Examples Section */}
            <section className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
              <button
                type="button"
                onClick={() => toggleSection('examples')}
                className="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 text-left hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <div className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-indigo-500" />
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                    {t('roiExplanation.examples.title', 'Value Examples')}
                  </h3>
                </div>
                {expandedSections.examples ? (
                  <ChevronUp className="h-5 w-5 text-gray-500" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-gray-500" />
                )}
              </button>

              {expandedSections.examples && (
                <div className="p-4">
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                    {t('roiExplanation.examples.description',
                      'Sample artifact valuations using Senior seniority level:'
                    )}
                  </p>

                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-200 dark:border-gray-700">
                          <th className="text-left py-2 px-2 text-gray-600 dark:text-gray-400 font-medium">Artifact</th>
                          <th className="text-left py-2 px-2 text-gray-600 dark:text-gray-400 font-medium">Role</th>
                          <th className="text-center py-2 px-2 text-gray-600 dark:text-gray-400 font-medium">
                            <Clock className="h-3 w-3 inline" /> Hours
                          </th>
                          <th className="text-center py-2 px-2 text-gray-600 dark:text-gray-400 font-medium">Rate</th>
                          <th className="text-right py-2 px-2 text-gray-600 dark:text-gray-400 font-medium">Value</th>
                        </tr>
                      </thead>
                      <tbody>
                        {ARTIFACT_EXAMPLES.map((ex) => (
                          <tr key={ex.type} className="border-b border-gray-100 dark:border-gray-800">
                            <td className="py-2 px-2 text-gray-900 dark:text-gray-100">{ex.type.replace('_', ' ')}</td>
                            <td className="py-2 px-2 text-gray-600 dark:text-gray-400">{ex.role}</td>
                            <td className="py-2 px-2 text-center font-mono text-gray-600 dark:text-gray-400">{ex.hours}h</td>
                            <td className="py-2 px-2 text-center font-mono text-gray-600 dark:text-gray-400">${ex.rate}</td>
                            <td className="py-2 px-2 text-right font-mono text-green-600 font-medium">${ex.value}</td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot>
                        <tr className="bg-gray-50 dark:bg-gray-800">
                          <td colSpan={4} className="py-2 px-2 text-right font-medium text-gray-900 dark:text-gray-100">
                            {t('roiExplanation.examples.total', 'Total Artifact Value:')}
                          </td>
                          <td className="py-2 px-2 text-right font-mono text-green-600 font-bold">
                            ${ARTIFACT_EXAMPLES.reduce((sum, ex) => sum + ex.value, 0).toLocaleString()}
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>

                  <div className="mt-4 bg-green-50 dark:bg-green-900/20 rounded-lg p-3">
                    <p className="text-sm text-green-800 dark:text-green-200">
                      <strong>📈 Example ROI:</strong> If token cost was $0.85, ROI = ($1,051 - $0.85) / $0.85 × 100% = <strong>123,547%</strong>
                    </p>
                  </div>
                </div>
              )}
            </section>

            {/* Footer note */}
            <div className="text-xs text-gray-500 dark:text-gray-400 bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3">
              <strong>💡</strong> {t('roiExplanation.note',
                'ROI calculations use industry-standard consulting rates. Squad configuration can be customized per project to match your team\'s actual rates and roles.'
              )}
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
