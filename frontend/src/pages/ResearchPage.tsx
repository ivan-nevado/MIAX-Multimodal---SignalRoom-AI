import { useSearchParams } from 'react-router-dom';
import { ModalitiesPanel } from '@/components/files/ModalitiesPanel';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { RecentInvestigations } from '@/features/investigations/RecentInvestigations';
import { ResearchComposer } from '@/features/investigations/ResearchComposer';

export default function ResearchPage() {
  const [params] = useSearchParams();
  const symbol = params.get('symbol');
  const name = params.get('name');
  return (
    <div>
      <PageHeader
        title="Research"
        subtitle="Research less. Understand more. From market movement to evidence in minutes."
      />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
        <ResearchComposer
          initialAsset={
            symbol
              ? { symbol, name: name ?? symbol, asset_type: 'equity', exchange: null, source: 'alias' }
              : null
          }
        />
        <ModalitiesPanel />
      </div>
      <Card className="mt-6">
        <CardHeader title="Recent investigations" />
        <CardBody className="pt-2">
          <RecentInvestigations limit={10} />
        </CardBody>
      </Card>
    </div>
  );
}
