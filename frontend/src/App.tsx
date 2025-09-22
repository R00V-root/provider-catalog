import { FormEvent, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { AdjustmentsHorizontalIcon, ArrowsUpDownIcon } from "@heroicons/react/24/outline";
import { XMarkIcon } from "@heroicons/react/24/solid";
import clsx from "clsx";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface FacetCount {
  key: "provider" | "brand" | "category";
  value: string;
  label: string;
  count: number;
}

export interface ProductSummary {
  id: string;
  sku: string;
  name: string;
  description?: string | null;
  brand?: { id: string; name: string } | null;
  default_category?: { id: string; name: string } | null;
  lowest_price?: number | null;
  highest_price?: number | null;
  provider_count: number;
}

export interface ProviderSummary {
  id: string;
  name: string;
  slug: string;
}

export interface ProviderOffer {
  id: string;
  provider: ProviderSummary;
  unit_of_measure?: string | null;
  currency: string;
  list_price?: number | null;
  price?: number | null;
  inventory_quantity?: number | null;
  inventory_updated_at?: string | null;
}

export interface SearchResponse {
  results: ProductSummary[];
  total: number;
  facets: Record<string, FacetCount[]>;
}

export interface CompareResponse {
  sku: string;
  offers: ProviderOffer[];
}

type SortOption = "relevance" | "price" | "price_desc" | "name" | "name_desc";
type FilterKey = "provider" | "brand" | "category";

type FilterState = Record<FilterKey, Set<string>>;

const createEmptyFilters = (): FilterState => ({
  provider: new Set<string>(),
  brand: new Set<string>(),
  category: new Set<string>()
});

interface UseSearchParams {
  query: string;
  filters: string;
  sort: SortOption;
  page: number;
}

const useSearch = ({ query, filters, sort, page }: UseSearchParams) => {
  const [data, setData] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await axios.get<SearchResponse>(`${API_BASE_URL}/search`, {
          params: {
            q: query || undefined,
            filters: filters || undefined,
            sort,
            page
          },
          signal: controller.signal
        });
        setData(response.data);
      } catch (err) {
        if (!axios.isCancel(err)) {
          setError("Unable to load search results");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    return () => controller.abort();
  }, [query, filters, sort, page]);

  return { data, loading, error };
};

const buildFilterString = (filters: FilterState): string => {
  const segments: string[] = [];
  (Object.keys(filters) as FilterKey[]).forEach((key) => {
    const values = Array.from(filters[key]);
    if (values.length > 0) {
      segments.push(`${key}:${values.join(",")}`);
    }
  });
  return segments.join(";");
};

interface FacetListProps {
  title: string;
  items: FacetCount[];
  selected: Set<string>;
  onToggle: (value: string) => void; // eslint-disable-line no-unused-vars
}

const FacetList = ({ title, items, selected, onToggle }: FacetListProps) => (
  <div className="mb-6">
    <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-3">{title}</h3>
    <ul className="space-y-2">
      {items.map((item) => (
        <li key={item.value}>
          <label className="flex items-center justify-between text-sm text-gray-700">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                className="rounded border-gray-300 text-primary focus:ring-primary"
                checked={selected.has(item.value)}
                onChange={() => onToggle(item.value)}
              />
              <span>{item.label}</span>
            </div>
            <span className="text-gray-400">{item.count}</span>
          </label>
        </li>
      ))}
      {items.length === 0 && <li className="text-sm text-gray-400">No options</li>}
    </ul>
  </div>
);

interface CompareDrawerProps {
  open: boolean;
  sku: string | null;
  offers: ProviderOffer[];
  loading: boolean;
  onClose: () => void;
}

const CompareDrawer = ({ open, sku, offers, loading, onClose }: CompareDrawerProps) => (
  <div
    className={clsx(
      "fixed inset-y-0 right-0 max-w-md w-full bg-white shadow-xl transform transition-transform duration-200 z-40",
      open ? "translate-x-0" : "translate-x-full"
    )}
  >
    <div className="flex items-center justify-between px-4 py-3 border-b">
      <div>
        <p className="text-xs uppercase text-gray-400">Price comparison</p>
        <h2 className="text-lg font-semibold">{sku || "Select a SKU"}</h2>
      </div>
      <button
        type="button"
        onClick={onClose}
        className="p-2 text-gray-500 hover:text-gray-700"
        aria-label="Close compare drawer"
      >
        <XMarkIcon className="h-5 w-5" />
      </button>
    </div>
    <div className="p-4 space-y-3 overflow-y-auto h-full">
      {loading && <p className="text-sm text-gray-500">Loading offers…</p>}
      {!loading && offers.length === 0 && <p className="text-sm text-gray-500">No offers found.</p>}
      {offers.map((offer) => {
        const numericPrice = offer.price ?? offer.list_price;
        return (
          <div key={offer.id} className="border rounded-lg p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-gray-800">{offer.provider.name}</p>
                <p className="text-xs text-gray-500">{offer.unit_of_measure ?? "each"}</p>
              </div>
              <div className="text-right">
                <p className="text-lg font-bold text-primary">
                  {numericPrice !== null && numericPrice !== undefined
                    ? `${offer.currency} ${numericPrice.toFixed(2)}`
                    : "Contact"}
                </p>
                {offer.list_price && offer.price && offer.list_price !== offer.price && (
                  <p className="text-xs text-gray-500">List: {offer.list_price.toFixed(2)}</p>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  </div>
);

const App = () => {
  const [searchInput, setSearchInput] = useState("");
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<FilterState>(createEmptyFilters);
  const [sort, setSort] = useState<SortOption>("relevance");
  const [page, setPage] = useState(0);
  const [activeTab, setActiveTab] = useState<"products" | "compare">("products");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [compareSku, setCompareSku] = useState<string | null>(null);
  const [drawerOffers, setDrawerOffers] = useState<ProviderOffer[]>([]);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [manualSku, setManualSku] = useState("");
  const [manualCompare, setManualCompare] = useState<CompareResponse | null>(null);
  const [manualLoading, setManualLoading] = useState(false);
  const [manualError, setManualError] = useState<string | null>(null);

  const filterString = useMemo(() => buildFilterString(filters), [filters]);

  const { data, loading, error } = useSearch({ query, filters: filterString, sort, page });

  useEffect(() => {
    setPage(0);
  }, [query, filterString, sort]);

  const toggleFilter = (key: FilterKey, value: string) => {
    setFilters((prev) => {
      const next: FilterState = {
        provider: new Set(prev.provider),
        brand: new Set(prev.brand),
        category: new Set(prev.category)
      };
      const selectedSet = next[key];
      if (selectedSet.has(value)) {
        selectedSet.delete(value);
      } else {
        selectedSet.add(value);
      }
      return next;
    });
  };

  const clearFilters = () => setFilters(createEmptyFilters());

  const submitSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setQuery(searchInput.trim());
  };

  const openCompareDrawer = async (sku: string) => {
    setCompareSku(sku);
    setDrawerOpen(true);
    setDrawerLoading(true);
    try {
      const response = await axios.get<CompareResponse>(`${API_BASE_URL}/compare`, {
        params: { sku }
      });
      setDrawerOffers(response.data.offers);
    } catch (err) {
      if (!axios.isCancel(err)) {
        setDrawerOffers([]);
      }
    } finally {
      setDrawerLoading(false);
    }
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
    setCompareSku(null);
    setDrawerOffers([]);
  };

  const runManualCompare = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!manualSku.trim()) {
      setManualError("Enter a SKU to compare");
      return;
    }
    setManualError(null);
    setManualLoading(true);
    try {
      const response = await axios.get<CompareResponse>(`${API_BASE_URL}/compare`, {
        params: { sku: manualSku.trim() }
      });
      setManualCompare(response.data);
    } catch (err) {
      if (!axios.isCancel(err)) {
        setManualError("No offers found for that SKU");
        setManualCompare(null);
      }
    } finally {
      setManualLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b shadow-sm">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-primary">Procurement Provider Catalog</h1>
              <p className="text-sm text-gray-500">
                Fast, auditable discovery across NASPO-style vendor listings.
              </p>
            </div>
            <form onSubmit={submitSearch} className="w-full sm:w-96">
              <div className="relative">
                <input
                  type="search"
                  placeholder="Search products, SKUs, descriptions…"
                  value={searchInput}
                  onChange={(event) => setSearchInput(event.target.value)}
                  className="w-full rounded-lg border border-gray-300 bg-white py-2 pl-3 pr-12 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40"
                />
                <button
                  type="submit"
                  className="absolute inset-y-0 right-0 flex items-center px-3 text-sm font-medium text-primary"
                >
                  Search
                </button>
              </div>
            </form>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6 flex gap-6">
        <aside className="hidden lg:block w-64 flex-shrink-0">
          <div className="bg-white rounded-xl border p-4 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Filters</h2>
              <button
                type="button"
                onClick={clearFilters}
                className="text-xs text-primary hover:text-primary-light"
              >
                Clear
              </button>
            </div>
            <FacetList
              title="Providers"
              items={data?.facets.provider ?? []}
              selected={filters.provider}
              onToggle={(value) => toggleFilter("provider", value)}
            />
            <FacetList
              title="Categories"
              items={data?.facets.category ?? []}
              selected={filters.category}
              onToggle={(value) => toggleFilter("category", value)}
            />
            <FacetList
              title="Brands"
              items={data?.facets.brand ?? []}
              selected={filters.brand}
              onToggle={(value) => toggleFilter("brand", value)}
            />
          </div>
        </aside>

        <section className="flex-1">
          <div className="mb-4">
            <div className="flex items-center gap-4">
              <div className="bg-white rounded-full p-1 shadow-sm">
                <nav className="flex">
                  {[
                    { id: "products", label: "Products" },
                    { id: "compare", label: "Price Compare" }
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      type="button"
                      onClick={() => setActiveTab(tab.id as "products" | "compare")}
                      className={clsx(
                        "px-4 py-1.5 text-sm font-medium rounded-full transition",
                        activeTab === tab.id
                          ? "bg-primary text-white shadow"
                          : "text-gray-600 hover:text-primary"
                      )}
                    >
                      {tab.label}
                    </button>
                  ))}
                </nav>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <AdjustmentsHorizontalIcon className="h-5 w-5" />
                <span>{data?.total ?? 0} results</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <ArrowsUpDownIcon className="h-4 w-4" />
                <select
                  value={sort}
                  onChange={(event) => setSort(event.target.value as SortOption)}
                  className="rounded-md border-gray-300 text-sm focus:border-primary focus:ring-primary"
                >
                  <option value="relevance">Relevance</option>
                  <option value="price">Lowest price</option>
                  <option value="price_desc">Highest price</option>
                  <option value="name">Name (A-Z)</option>
                  <option value="name_desc">Name (Z-A)</option>
                </select>
              </div>
            </div>
          </div>

          {activeTab === "products" && (
            <div className="space-y-4">
              {loading && <p className="text-sm text-gray-500">Loading products…</p>}
              {error && <p className="text-sm text-red-500">{error}</p>}
              {!loading && (data?.results.length ?? 0) === 0 && (
                <p className="text-sm text-gray-500">No products match your filters yet.</p>
              )}
              {data?.results.map((product) => {
                const priceRange = [product.lowest_price, product.highest_price].filter(
                  (price) => price !== null && price !== undefined
                ) as number[];
                const priceLabel =
                  priceRange.length === 0
                    ? "Pricing unavailable"
                    : priceRange.length === 1
                    ? `$${priceRange[0].toFixed(2)}`
                    : `$${priceRange[0].toFixed(2)} – $${priceRange[1].toFixed(2)}`;
                return (
                  <div key={product.id} className="bg-white border rounded-xl shadow-sm p-5">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <p className="text-xs uppercase text-gray-400">{product.sku}</p>
                        <h3 className="text-lg font-semibold text-gray-900">{product.name}</h3>
                        <p className="text-sm text-gray-600 max-h-16 overflow-hidden">
                          {product.description ?? "No description provided."}
                        </p>
                        <div className="mt-2 flex flex-wrap gap-3 text-xs text-gray-500">
                          {product.brand && <span>Brand: {product.brand.name}</span>}
                          {product.default_category && <span>Category: {product.default_category.name}</span>}
                          <span>Vendors: {product.provider_count}</span>
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        <p className="text-sm font-medium text-primary">{priceLabel}</p>
                        <button
                          type="button"
                          onClick={() => openCompareDrawer(product.sku)}
                          className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white shadow hover:bg-primary-light focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
                        >
                          Compare prices
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {activeTab === "compare" && (
            <div className="bg-white border rounded-xl shadow-sm p-6">
              <form onSubmit={runManualCompare} className="flex flex-col sm:flex-row gap-3">
                <div className="flex-1">
                  <label className="block text-xs uppercase text-gray-400">Manufacturer part number</label>
                  <input
                    type="text"
                    value={manualSku}
                    onChange={(event) => setManualSku(event.target.value)}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:ring-primary"
                    placeholder="Enter SKU"
                  />
                </div>
                <button
                  type="submit"
                  className="self-end rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white shadow hover:bg-primary-light"
                >
                  Compare
                </button>
              </form>
              {manualError && <p className="mt-3 text-sm text-red-500">{manualError}</p>}
              {manualLoading && <p className="mt-3 text-sm text-gray-500">Loading offers…</p>}
              {manualCompare && (
                <div className="mt-4 space-y-3">
                  <h3 className="text-sm font-semibold text-gray-700">
                    Offers for <span className="font-mono">{manualCompare.sku}</span>
                  </h3>
                  {manualCompare.offers.length === 0 && (
                    <p className="text-sm text-gray-500">No offers available.</p>
                  )}
                  {manualCompare.offers.map((offer) => {
                    const numericPrice = offer.price ?? offer.list_price;
                    return (
                      <div key={offer.id} className="border rounded-lg p-4 flex items-center justify-between">
                        <div>
                          <p className="text-sm font-semibold text-gray-800">{offer.provider.name}</p>
                          <p className="text-xs text-gray-500">{offer.unit_of_measure ?? "each"}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-bold text-primary">
                            {numericPrice !== null && numericPrice !== undefined
                              ? `${offer.currency} ${numericPrice.toFixed(2)}`
                              : "Contact"}
                          </p>
                          {offer.list_price && offer.price && offer.list_price !== offer.price && (
                            <p className="text-xs text-gray-500">List: {offer.list_price.toFixed(2)}</p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </section>
      </main>

      <CompareDrawer
        open={drawerOpen}
        sku={compareSku}
        offers={drawerOffers}
        loading={drawerLoading}
        onClose={closeDrawer}
      />
    </div>
  );
};

export default App;
