import type { ActivityCard } from "@/lib/types";
import UrgentCard from "./UrgentCard";

interface Props {
  cards: ActivityCard[];
}

export default function UrgentSection({ cards }: Props) {
  if (cards.length === 0) return null;

  return (
    <>
      <div className="section-head">
        <h3>🔥 곧 마감</h3>
        <span className="meta">마감 3일 이내</span>
      </div>
      <div className="urgent-row">
        {cards.map((card) => (
          <UrgentCard key={card.id} card={card} />
        ))}
      </div>
    </>
  );
}
