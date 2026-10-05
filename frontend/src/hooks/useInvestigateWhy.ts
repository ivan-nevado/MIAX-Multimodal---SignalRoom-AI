import { useNavigate } from 'react-router-dom';
import { useCreateInvestigation } from './queries';

/** One click "Why?" → queue an investigation and open its live progress page. */
export function useInvestigateWhy() {
  const navigate = useNavigate();
  const create = useCreateInvestigation();
  const investigate = async (symbol: string, name?: string) => {
    const res = await create.mutateAsync({
      asset: symbol,
      question: `Why did ${name ?? symbol} move today?`,
      generate_audio: true,
    });
    navigate(`/app/investigation/${res.investigation_id}`);
  };
  return { investigate, pending: create.isPending, error: create.error as Error | null };
}
