import { tmdbImg } from '../api';
import type { TmdbPerson } from '../types';

export default function PersonCard({
  person,
  onClick,
}: {
  person: TmdbPerson;
  onClick: (person: TmdbPerson) => void;
}) {
  const photo = tmdbImg.profile(person.profile_path);
  return (
    <button
      type="button"
      onClick={() => onClick(person)}
      className="group relative w-full aspect-[2/3] rounded-lg overflow-hidden bg-card border border-border
                  hover:border-accent/50 transition-all hover:-translate-y-1 hover:shadow-xl
                  hover:shadow-black/40 text-left"
    >
      {photo ? (
        <img
          loading="lazy"
          src={photo}
          alt={person.name}
          className="absolute inset-0 w-full h-full object-cover"
        />
      ) : (
        <div
          className="absolute inset-0 flex items-center justify-center font-mono font-bold text-[80px]"
          style={{
            background: `linear-gradient(135deg, hsl(${(person.name.charCodeAt(0) * 7) % 360}, 40%, 25%), hsl(${(person.name.charCodeAt(0) * 7 + 40) % 360}, 50%, 15%))`,
            color: 'rgba(255,255,255,0.14)',
          }}
        >
          {person.name[0]}
        </div>
      )}
      <div className="absolute top-2 right-2 px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase bg-black/70 text-white">
        Actor
      </div>
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/95 via-black/60 to-transparent p-2.5 pt-6">
        <div className="font-semibold text-xs leading-tight line-clamp-2 mb-1">{person.name}</div>
        {person.known_for_department && (
          <div className="text-[10px] text-white/70">{person.known_for_department}</div>
        )}
      </div>
    </button>
  );
}
