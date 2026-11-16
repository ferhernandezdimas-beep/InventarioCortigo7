import Decimal from "decimal.js";
import type {
  Command,
  Ingredient,
  Product,
  QueueItem,
  Snapshot,
} from "./types";

Decimal.set({ precision: 40, rounding: Decimal.ROUND_HALF_UP });
export const money = (value: string | Decimal) =>
  "$" + new Decimal(value).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
export const quantity = (value: string | Decimal) =>
  new Decimal(value).toDecimalPlaces(6).toString();
export const normalize = (s: string) =>
  s
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
export const localDay = (now = new Date()) =>
  new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Mexico_City",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(now);
export const kindLabel = (kind: string) =>
  ({
    receipt: "Entrada",
    issue: "Salida",
    sale: "Venta",
    waste: "Merma",
    adjustment: "Conteo",
    sale_cancel: "Cancelación",
    receipt_reversal: "Reversión de entrada",
    reversal: "Reversión",
    opening: "Apertura",
  })[kind] || kind;
export function decimalInput(
  value: string,
  places = 6,
  positive = true,
): string {
  const normalized = value.trim().replace(",", ".");
  if (!new RegExp(`^\\d+(?:\\.\\d{1,${places}})?$`).test(normalized))
    throw new Error(`Usa un número con hasta ${places} decimales.`);
  const number = new Decimal(normalized);
  if (number.gte("1000000000000") || (positive ? number.lte(0) : number.lt(0)))
    throw new Error("La cantidad está fuera del rango permitido.");
  return number.toFixed(places);
}
export function effectiveInventory(
  snapshot: Snapshot,
  now = new Date(),
): Ingredient[] {
  const today = localDay(now);
  return snapshot.ingredients.map((item) => ({
    ...item,
    available: snapshot.lots
      .filter(
        (l) =>
          l.ingredient_id === item.id &&
          (!l.expires_on || l.expires_on >= today),
      )
      .reduce((total, l) => total.add(l.quantity), new Decimal(0))
      .toFixed(6),
  }));
}
export function cartTotal(
  products: Product[],
  cart: Record<number, number>,
): string {
  return Object.entries(cart)
    .reduce((total, [id, count]) => {
      const item = products.find((p) => p.id === Number(id));
      if (!item || !Number.isInteger(count) || count < 1 || count > 9999)
        throw new Error("Revisa las cantidades del carrito.");
      return total.add(new Decimal(item.price).mul(count));
    }, new Decimal(0))
    .toFixed(2);
}
export function saleCommand(
  key: string,
  products: Product[],
  cart: Record<number, number>,
  method: "cash" | "card" | "transfer",
  received: string,
): Command {
  if (!Object.keys(cart).length) throw new Error("Agrega un producto.");
  const total = cartTotal(products, cart);
  const paid = method === "cash" ? decimalInput(received, 2, false) : undefined;
  if (paid && new Decimal(paid).lt(total))
    throw new Error("El efectivo recibido no cubre el total.");
  return {
    key,
    kind: "sale",
    method,
    received: paid,
    expected_total: total,
    expected_recipes: Object.fromEntries(
      Object.keys(cart).map((id) => [
        id,
        products.find((p) => p.id === Number(id))!.recipe_version,
      ]),
    ),
    lines: Object.entries(cart).map(([id, count]) => ({
      menu_item_id: Number(id),
      quantity: String(count),
    })),
  };
}
export function mayDiscard(item: QueueItem): boolean {
  // Unknown outcomes must be retried with exactly the same key and body.
  return (
    item.status === "conflict" || (item.status === "pending" && !item.attempted)
  );
}
export function preparedPortions(
  product: Product,
  ingredients: Ingredient[],
): number | null {
  if (!product.requirements.length) return null;
  return product.requirements.reduce((max, requirement) => {
    const item = ingredients.find((i) => i.id === requirement.ingredient_id);
    return Math.min(
      max,
      item
        ? new Decimal(item.available)
            .div(requirement.quantity)
            .floor()
            .toNumber()
        : 0,
    );
  }, Number.MAX_SAFE_INTEGER);
}
export type Answer = {
  text: string;
  action?: "inventory" | "pos" | "sync";
  actionLabel?: string;
};
export function assistant(
  question: string,
  snapshot: Snapshot,
  queue: QueueItem[],
  now = new Date(),
): Answer {
  const q = normalize(question),
    rows = effectiveInventory(snapshot, now),
    today = localDay(now);
  const note = `\n\nConsulta local del ${new Date(snapshot.server_time).toLocaleString("es-MX")}. Las operaciones pendientes aún no están confirmadas.`;
  if (/sincron|pendiente|conexion/.test(q)) {
    const pending = queue.filter((i) => i.status === "pending").length,
      conflicts = queue.filter((i) => i.status === "conflict").length;
    return {
      text: `Tienes ${pending} operaciones pendientes y ${conflicts} por revisar. Con internet, sincroniza para validar existencias, recetas y permisos en Render. Si hay un conflicto, la operación completa se conserva para revisión.`,
      action: "sync",
      actionLabel: "Ver sincronización",
    };
  }
  if (/caduc|venc|lote/.test(q) && rows.length) {
    const until = new Date(today + "T12:00:00Z");
    until.setUTCDate(until.getUTCDate() + snapshot.expiry_alert_days);
    const selected = snapshot.lots
      .filter(
        (l) => l.expires_on && l.expires_on <= until.toISOString().slice(0, 10),
      )
      .sort((a, b) => a.expires_on!.localeCompare(b.expires_on!));
    return {
      text: selected.length
        ? `${selected.length} lotes requieren atención:\n` +
          selected
            .slice(0, 8)
            .map((l) => {
              const item = rows.find((i) => i.id === l.ingredient_id);
              return `• ${item?.name || "Ingrediente inactivo"}: ${quantity(l.quantity)} ${item?.unit || ""}, ${l.expires_on! < today ? "CADUCADO" : "vence"} ${l.expires_on}.`;
            })
            .join("\n") +
          "\nLos caducados se excluyen de la disponibilidad; las salidas usan PEPS." +
          note
        : "No hay lotes próximos a caducar en la información descargada." +
          note,
      action: "inventory",
      actionLabel: "Ver inventario",
    };
  }
  if (/compr|repon|bajo|minim|falta/.test(q) && rows.length) {
    const low = rows.filter((i) => new Decimal(i.available).lte(i.minimum));
    return {
      text: low.length
        ? "Tu lista sugerida de reposición:\n" +
          low
            .slice(0, 10)
            .map((i) => {
              const target = i.maximum || i.minimum;
              const needed = Decimal.max(
                new Decimal(target).sub(i.available),
                0,
              );
              const supplier = snapshot.suppliers.find(
                (s) => s.id === i.supplier_id,
              )?.name;
              return `• ${i.name}: quedan ${quantity(i.available)} ${i.unit}; ${needed.gt(0) ? "reponer " + quantity(needed) + " " + i.unit : "revisar el mínimo configurado"}${supplier ? " · " + supplier : ""}.`;
            })
            .join("\n") +
          "\nSugerencia basada en mínimos y máximos; no genera una compra." +
          note
        : "Las existencias descargadas están por encima de sus mínimos." + note,
      action: "inventory",
      actionLabel: "Revisar existencias",
    };
  }
  if (
    /prepar|cocin|platillo|receta|vender/.test(q) &&
    snapshot.products.some((p) => p.requirements.length)
  ) {
    const products = snapshot.products
      .map((p) => ({ product: p, portions: preparedPortions(p, rows) }))
      .filter((p) => p.portions !== null && p.portions > 0)
      .sort((a, b) => b.portions! - a.portions!);
    return {
      text:
        "Según el inventario descargado, puedes preparar por separado:\n" +
        (products
          .slice(0, 8)
          .map(
            (p) =>
              `• ${p.product.name}: hasta ${p.portions} porciones · ${money(p.product.price)}.`,
          )
          .join("\n") || "No hay porciones completas disponibles.") +
        "\nCada cálculo es independiente: los platillos comparten ingredientes y no se suman sus capacidades." +
        note,
      action: "pos",
      actionLabel: "Ir a productos",
    };
  }
  const match = rows.filter((i) =>
    normalize(i.name)
      .split(" ")
      .some((word) => word.length > 2 && q.includes(word)),
  );
  if (match.length)
    return {
      text:
        match
          .slice(0, 5)
          .map(
            (i) =>
              `${i.name}\n• Disponible: ${quantity(i.available)} ${i.unit}\n• Físico: ${quantity(i.physical)} ${i.unit}\n• Mínimo: ${quantity(i.minimum)} ${i.unit}`,
          )
          .join("\n\n") + note,
      action: "inventory",
      actionLabel: "Ver ingredientes",
    };
  if (
    /venta|vend|ingreso/.test(q) &&
    snapshot.user.permissions.includes("sales.read")
  ) {
    const sales = snapshot.sales.filter(
      (s) => !s.cancelled && localDay(new Date(s.created_at)) === today,
    );
    return {
      text:
        `En los últimos ${snapshot.sales.length} registros descargados hay ${sales.length} ventas vigentes de hoy, por ${money(sales.reduce((s, sale) => s.add(sale.total), new Decimal(0)))}. ${snapshot.user.role === "cashier" ? "Solo se incluyen tus ventas." : "Este resumen está limitado a los 100 registros más recientes."}` +
        note,
    };
  }
  return {
    text: `Soy C7, tu asistente de operación. Analizo los datos que ya descargaste y funciono sin internet. ${rows.length ? "Puedes preguntarme por un ingrediente, qué comprar, qué caduca o qué puedes preparar." : "Con tu permiso de caja puedo ayudarte con ventas y sincronización."}\n\nTambién te explico tus pendientes. No modifico inventario ni genero operaciones desde el chat.`,
  };
}
