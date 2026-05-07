import { Card } from "@/components/ui/card";
import { Pill } from "@/components/ui/pill";

export default function CapturePage() {
  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Pre-award capture intelligence</h1>
        <p className="text-sm text-secondary">
          Standalone subscription for GSI/FSI capture teams. Feasibility + LCAT + heat maps.
        </p>
      </header>
      <Card title="Heat maps">
        <p className="text-sm text-secondary">Connect /v1/capture/heatmap to populate.</p>
      </Card>
      <Card title="Pre-positioned candidate pools">
        <p className="text-sm text-secondary">Wire the capture service. <Pill tone="warning">empty</Pill></p>
      </Card>
    </div>
  );
}
