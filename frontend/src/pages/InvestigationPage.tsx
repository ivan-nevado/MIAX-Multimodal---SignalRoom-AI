import { useParams } from 'react-router-dom';
import { ErrorState, Skeleton } from '@/components/ui/states';
import { InvestigationView } from '@/features/investigations/InvestigationView';
import { useInvestigation } from '@/hooks/queries';

export default function InvestigationPage() {
  const { id } = useParams();
  const { data, isLoading, error, refetch } = useInvestigation(id);
  if (isLoading) return <Skeleton className="h-96 w-full" />;
  if (error || !data)
    return (
      <ErrorState
        title="Investigation unavailable"
        message={(error as Error | null)?.message}
        onRetry={() => void refetch()}
      />
    );
  return <InvestigationView investigation={data} />;
}
