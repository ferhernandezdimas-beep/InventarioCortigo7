export type User = {
  id: number;
  name: string;
  email: string;
  role: string;
  role_label: string;
  permissions: string[];
};
export type Session = { token: string; expires_at: string; user: User };
export type Ingredient = {
  id: number;
  name: string;
  code: string | null;
  category: string;
  unit: string;
  minimum: string;
  maximum: string | null;
  physical: string;
  available: string;
  known_value: string;
  unknown: string;
  supplier_id: number | null;
};
export type Lot = {
  id: number;
  ingredient_id: number;
  code: string | null;
  quantity: string;
  received_at: string;
  expires_on: string | null;
};
export type Product = {
  id: number;
  name: string;
  category: string;
  code: string | null;
  price: string;
  recipe_version: number;
  requirements: { ingredient_id: number; quantity: string }[];
};
export type Sale = {
  id: string;
  total: string;
  method: string;
  created_at: string;
  cancelled: boolean;
  items: { name: string; quantity: number; unit_price: string }[];
};
export type Snapshot = {
  categories?: { id: number; name: string }[];
  units?: { id: number; name: string; symbol: string }[];
  schema_version: number;
  server_time: string;
  user: User;
  expiry_alert_days: number;
  ingredients: Ingredient[];
  lots: Lot[];
  suppliers: { id: number; name: string }[];
  presentations: {
    id: number;
    ingredient_id: number;
    name: string;
    base_quantity: string;
  }[];
  products: Product[];
  operations: {
    id: string;
    kind: string;
    reason: string;
    created_at: string;
  }[];
  sales: Sale[];
};
export type ReceiptLine = {
  ingredient_id: number;
  quantity: string;
  unit_cost?: string | null;
  code?: string;
  expires_on?: string;
  presentation_id?: number;
};
export type InventoryCommand = {
  key: string;
  kind: "receipt" | "issue";
  reason: string;
  supplier_id?: number;
  reference?: string;
  lines: ReceiptLine[];
};
export type SaleCommand = {
  key: string;
  kind: "sale";
  lines: { menu_item_id: number; quantity: string }[];
  method: "cash" | "card" | "transfer";
  received?: string;
  expected_total: string;
  expected_recipes: Record<string, number>;
};
export type CatalogCommand = {
  key: string;
  kind:
    | "catalog.ingredient.create"
    | "catalog.category.create"
    | "catalog.supplier.create"
    | "catalog.presentation.create";
  data: Record<string, string | number | boolean | null>;
};
export type Command = InventoryCommand | SaleCommand | CatalogCommand;
export type QueueItem = {
  key: string;
  command: Command;
  label: string;
  created_at: string;
  status: "pending" | "conflict" | "confirmed";
  attempted: boolean;
  error: string | null;
  result_id: string | null;
};
