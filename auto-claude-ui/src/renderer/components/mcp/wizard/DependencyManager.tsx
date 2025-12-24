import { Card, CardContent } from '../../ui/card';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Plus, Trash2 } from 'lucide-react';

interface DependencyManagerProps {
  dependencies: string[];  // Array of "package>=version" strings
  onDependenciesChange: (dependencies: string[]) => void;
  onNext: () => void;
  onBack: () => void;
}

export function DependencyManager({
  dependencies,
  onDependenciesChange,
  onNext,
  onBack
}: DependencyManagerProps) {
  const handleAddDependency = () => {
    onDependenciesChange([...dependencies, '']);
  };

  const handleRemoveDependency = (index: number) => {
    const newDependencies = dependencies.filter((_, i) => i !== index);
    onDependenciesChange(newDependencies);
  };

  const handleEditDependency = (index: number, value: string) => {
    const newDependencies = [...dependencies];
    newDependencies[index] = value;
    onDependenciesChange(newDependencies);
  };

  const isFastMCP = (dep: string) => {
    return dep.startsWith('fastmcp');
  };

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold">Manage Dependencies</h3>
        <p className="text-sm text-muted-foreground">
          Configure Python package dependencies for your FastMCP server
        </p>
      </div>

      {/* Dependencies List */}
      <Card>
        <CardContent className="pt-6">
          <div className="space-y-3">
            {dependencies.map((dep, index) => (
              <div key={index} className="flex items-center gap-2">
                <Input
                  value={dep}
                  onChange={(e) => handleEditDependency(index, e.target.value)}
                  placeholder="package>=version"
                  className="flex-1"
                  aria-label={`Dependency ${index + 1}`}
                />
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handleRemoveDependency(index)}
                  disabled={isFastMCP(dep)}
                  aria-label={`Remove ${dep || 'dependency'}`}
                >
                  <Trash2 className={`h-4 w-4 ${isFastMCP(dep) ? 'text-muted' : 'text-destructive'}`} />
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Add Dependency Button */}
      <Button
        variant="outline"
        onClick={handleAddDependency}
        className="w-full"
      >
        <Plus className="h-4 w-4 mr-2" />
        Add Dependency
      </Button>

      {/* Helper Text */}
      <div className="text-sm text-muted-foreground bg-muted/50 p-3 rounded-md">
        <p>uv handles virtual environment automatically</p>
        <p className="mt-1 text-xs">
          Format: <code className="bg-background px-1 py-0.5 rounded">package_name&gt;=version</code>
          {' '}(e.g., <code className="bg-background px-1 py-0.5 rounded">httpx&gt;=0.25.0</code>)
        </p>
        <p className="mt-1 text-xs">
          Note: <code className="bg-background px-1 py-0.5 rounded">fastmcp&gt;=0.1.0</code> is required and cannot be removed
        </p>
      </div>

      {/* Navigation Buttons */}
      <div className="flex justify-between pt-4">
        <Button variant="outline" onClick={onBack}>
          Back
        </Button>
        <Button onClick={onNext}>
          Next
        </Button>
      </div>
    </div>
  );
}
