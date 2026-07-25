import type { ActivityCard as ActivityCardType } from "@/lib/types";
import ActivityCard from "./ActivityCard";
import EmptyState from "./EmptyState";

interface Props {
  cards: ActivityCardType[];
  emptyText?: string;
}

export default function CardList({ cards, emptyText = "표시할 공고가 없어요." }: Props) {
  if (cards.length === 0) {
    return <EmptyState text={emptyText} />;
  }
  return (
    <div className="cards">
      {cards.map((card) => (
        <ActivityCard key={card.id} card={card} />
      ))}
    </div>
  );
}
