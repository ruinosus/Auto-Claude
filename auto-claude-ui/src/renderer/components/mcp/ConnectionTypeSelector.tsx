/**
 * ConnectionTypeSelector Component
 *
 * Radio button selector for choosing MCP server connection type:
 * - HTTP/HTTPS: REST API servers
 * - Standard I/O: Command-line executable servers
 * - Server-Sent Events: Real-time streaming servers
 */
import { Label } from '../ui/label';
import { RadioGroup, RadioGroupItem } from '../ui/radio-group';

interface ConnectionTypeSelectorProps {
  value: 'http' | 'stdio' | 'sse';
  onChange: (value: 'http' | 'stdio' | 'sse') => void;
}

export function ConnectionTypeSelector({ value, onChange }: ConnectionTypeSelectorProps) {
  return (
    <div className="space-y-4">
      <Label>Connection Type</Label>
      <RadioGroup value={value} onValueChange={onChange}>
        <div className="flex items-center space-x-2">
          <RadioGroupItem value="http" id="http" />
          <Label htmlFor="http" className="font-normal cursor-pointer">
            <div>
              <div className="font-semibold">HTTP/HTTPS</div>
              <div className="text-sm text-muted-foreground">
                Connect to REST API servers over HTTP/HTTPS
              </div>
            </div>
          </Label>
        </div>

        <div className="flex items-center space-x-2">
          <RadioGroupItem value="stdio" id="stdio" />
          <Label htmlFor="stdio" className="font-normal cursor-pointer">
            <div>
              <div className="font-semibold">Standard I/O</div>
              <div className="text-sm text-muted-foreground">
                Launch command-line executable servers
              </div>
            </div>
          </Label>
        </div>

        <div className="flex items-center space-x-2">
          <RadioGroupItem value="sse" id="sse" />
          <Label htmlFor="sse" className="font-normal cursor-pointer">
            <div>
              <div className="font-semibold">Server-Sent Events</div>
              <div className="text-sm text-muted-foreground">
                Connect to real-time streaming servers via SSE
              </div>
            </div>
          </Label>
        </div>
      </RadioGroup>
    </div>
  );
}
