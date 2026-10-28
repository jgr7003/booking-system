import { Link, useSearch } from "@tanstack/react-router";
import { TopBar } from "@/components/layout/TopBar";
import { useTrip } from "@/features/trip/public";
import { SearchForm } from "./SearchForm";

/** Design board "Búsqueda". */
export function SearchPage() {
  const search = useSearch({ from: "/" });
  const tripCount = useTrip((s) => s.order.length);

  return (
    <>
      <TopBar className="max-w-[1200px] sm:px-6">
        <nav className="ml-auto flex gap-5 text-[14px]">
          <Link to="/trip" className="text-white underline hover:text-white">
            Tu viaje{tripCount > 0 ? ` (${tripCount})` : ""}
          </Link>
        </nav>
      </TopBar>
      <main className="mx-auto flex max-w-[1200px] flex-col gap-5 px-4 pt-4 pb-16 sm:px-6 sm:pt-10">
        <h1 className="text-[22px] font-bold sm:text-[28px]">Buscar vuelos</h1>
        <SearchForm initial={search} />
      </main>
    </>
  );
}
