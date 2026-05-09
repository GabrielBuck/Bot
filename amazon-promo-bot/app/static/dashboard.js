const state = {
  amazonStatus: null,
  summary: null,
  topBooks: null,
  topItems: [],
  products: [],
  promotions: [],
  openMessage: null,
};

document.addEventListener("DOMContentLoaded", () => {
  bindFilters();
  bindActions();
  refreshAll();
});

function bindFilters() {
  [
    "filter-search",
    "filter-category",
    "filter-status",
    "filter-priority",
    "filter-format",
  ].forEach((id) => {
    const element = document.getElementById(id);
    if (!element) return;
    element.addEventListener("input", renderProductsTable);
    element.addEventListener("change", renderProductsTable);
  });
}

function bindActions() {
  document.body.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;

    const action = button.dataset.action;
    const id = Number(button.dataset.id);

    try {
      if (action === "refresh-data") await refreshAll();
      if (action === "refresh-prices") await refreshPrices();
      if (action === "scroll-links-ready") scrollToLinksReady();
      if (action === "scroll-pending") scrollToPending();
      if (action === "quick-filter") applyQuickFilter(button.dataset.status || "all");
      if (action === "clear-filters") clearFilters();
      if (action === "open-search") openSearch(id);
      if (action === "open-product") openProduct(id);
      if (action === "copy-link") await copyAffiliateLink(id);
      if (action === "copy-message") await copyMessage(id);
      if (action === "open-message") await openMessageModal(id);
      if (action === "close-message-modal") closeMessageModal();
      if (action === "copy-open-message") await copyOpenMessage();
      if (action === "save-asin") {
        await saveAsin(id, getInputValue(button.dataset.input || `asin-input-${id}`));
      }
      if (action === "toggle-asin-editor") toggleAsinEditor(id);
      if (action === "toggle-active") await toggleActive(id);
      if (action === "copy-all-ready") await copyAllReady();
    } catch (error) {
      showToast(error.message || "Erro inesperado", "error");
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMessageModal();
  });
}

async function refreshAll() {
  await Promise.all([
    loadHealth(),
    loadAmazonStatus(),
    loadSummary(),
    loadTopBooks(),
    loadProducts(),
    loadPromotions(),
  ]);
}

async function apiFetch(url, options = {}) {
  let response;
  try {
    response = await fetch(url, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
  } catch (error) {
    throw new Error("API fora do ar ou inacessível.");
  }

  if (!response.ok) {
    let detail = `Erro ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch (error) {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }

  return response.json();
}

async function loadHealth() {
  const statusElement = document.getElementById("api-status");
  try {
    await apiFetch("/health");
    statusElement.textContent = "API online";
    statusElement.className = "pill ok";
  } catch (error) {
    statusElement.textContent = "API indisponível";
    statusElement.className = "pill error";
  }
}

async function loadAmazonStatus() {
  state.amazonStatus = await apiFetch("/integrations/amazon/status");
  setText("status-source", state.amazonStatus.source_mode);
  setText("status-tag", yesNo(state.amazonStatus.has_associate_tag));
  setText("status-creators", yesNo(state.amazonStatus.has_creators_api_credentials));
  setText("status-prices", state.amazonStatus.can_fetch_live_prices ? "Ativa" : "Inativa");
  setText(
    "status-promotions",
    state.amazonStatus.can_detect_real_promotions ? "Disponíveis" : "Indisponíveis",
  );
  setText("status-message", state.amazonStatus.message);

  const banner = document.getElementById("amazon-banner");
  if (state.amazonStatus.can_fetch_live_prices) {
    banner.textContent = "Consulta real da Amazon ativa. Preços atualizados via API oficial.";
    banner.className = "success-banner";
  } else {
    banner.textContent = "Preços reais ainda não estão sendo consultados. Esta V1 usa lista fixa/manual. Produtos com link afiliado não significam promoção.";
    banner.className = "warning-banner";
  }
}

async function loadSummary() {
  state.summary = await apiFetch("/dashboard/summary");
  setText("summary-total", state.summary.total_products);
  setText("summary-ready", state.summary.ready_products);
  setText("summary-pending", state.summary.pending_asin);
  setText("summary-promotions", state.summary.verified_promotions);
  setText("summary-source", state.amazonStatus?.source_mode || "manual_fixed");
}

async function loadTopBooks() {
  state.topBooks = await apiFetch("/dashboard/top-books?max_per_category=2");
  renderTopBooks(state.topBooks);
}

function renderTopBooks(data) {
  const container = document.getElementById("top-books-container");
  state.topItems = (data.categories || []).flatMap((category) =>
    category.items.map((item) => ({ ...item, category: category.category, category_label: category.label })),
  );

  setText("top-books-title", data.title);
  setText("top-books-subtitle", data.subtitle);
  setText(
    "top-books-help",
    data.mode === "verified_promotions"
      ? "Estas promoções possuem preço verificado pela fonte oficial no horário indicado."
      : "Estes livros têm link afiliado pronto, mas o preço ainda precisa ser conferido manualmente na Amazon.",
  );

  if (!data.categories.length) {
    container.innerHTML = `
      <div class="empty-state slim">
        Nenhum link pronto para sugerir ainda. Valide ASINs para montar esta área.
      </div>
    `;
    return;
  }

  container.innerHTML = data.categories.map((category) => `
    <section class="category-row">
      <div class="category-row__heading">
        <h3>${escapeHtml(category.label)} · ${category.items.length} ${category.items.length === 1 ? "sugestão" : "sugestões"}</h3>
      </div>
      <div class="book-card-row">
        ${category.items.map((item) => renderMiniBookCard(item, category)).join("")}
      </div>
    </section>
  `).join("");
}

function renderMiniBookCard(item, category) {
  const isPromotion = item.status_label === "Promoção verificada";
  const priceBlock = isPromotion
    ? `
      ${item.list_price ? `<div class="price-old">De ${formatPrice(item.list_price)}</div>` : ""}
      <div class="price-current">Por ${formatPrice(item.current_price)}</div>
      ${item.discount_percent ? `<span class="discount-badge">-${item.discount_percent}%</span>` : ""}
    `
    : `<div class="price-muted">Preço não verificado</div>`;

  return `
    <article class="book-mini-card">
      <div class="book-card-summary">
        <div>
          <h4>${escapeHtml(item.title)}</h4>
          <p>${escapeHtml(item.author || "Autor não informado")}</p>
        </div>
        <div class="mini-meta">
          <span>${escapeHtml(category.label)}</span>
          <span class="status-badge ${isPromotion ? "promotion" : "ready"}">${escapeHtml(item.status_label)}</span>
        </div>
        <div class="mini-price">${priceBlock}</div>
      </div>

      <div class="book-card-expanded">
        <dl>
          <div><dt>ASIN</dt><dd>${escapeHtml(item.asin || "-")}</dd></div>
          <div><dt>Status</dt><dd>${escapeHtml(item.status_label)}</dd></div>
          <div><dt>Preço</dt><dd>${escapeHtml(item.price_label)}</dd></div>
          ${item.last_price_checked_at ? `<div><dt>Verificado</dt><dd>${formatDate(item.last_price_checked_at)}</dd></div>` : ""}
        </dl>
        <div class="short-link" title="${escapeAttr(item.affiliate_link || "")}">
          ${escapeHtml(item.affiliate_link || "Sem link afiliado")}
        </div>
        <div class="row-actions">
          <button class="button action-button-small" data-action="open-product" data-id="${item.id}" ${item.affiliate_link ? "" : "disabled"}>Abrir Amazon</button>
          <button class="button action-button-small" data-action="copy-link" data-id="${item.id}" ${item.affiliate_link ? "" : "disabled"}>Copiar link</button>
          <button class="button action-button-small" data-action="copy-message" data-id="${item.id}">Copiar mensagem</button>
          <button class="button primary action-button-small" data-action="open-message" data-id="${item.id}">Ver mensagem</button>
        </div>
      </div>
    </article>
  `;
}

async function loadProducts() {
  state.products = await apiFetch("/manual-products");
  updateCategoryFilter();
  updateFormatFilter();
  renderProductsTable();
  loadPendingProducts();
}

function loadPendingProducts() {
  renderPendingProducts();
}

async function loadPromotions() {
  const payload = await apiFetch("/promotions");
  state.promotions = payload.items || [];
  renderPromotions(payload.message);
}

function renderPromotions(message) {
  const container = document.getElementById("promotions-list");
  if (!state.promotions.length) {
    container.innerHTML = `
      <div class="empty-state slim">
        <strong>Nenhuma promoção real verificada ainda.</strong>
        <p>Por enquanto, o sistema possui links afiliados e mensagens prontas, mas ainda não consulta preços reais da Amazon.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = state.promotions.map((product) => `
    <article class="promotion-card">
      <div>
        <h3>${escapeHtml(product.title)}</h3>
        <p class="muted">${escapeHtml(product.author || "Autor não informado")}</p>
      </div>
      <div class="promotion-price">
        ${product.list_price ? `<span class="price-old">De ${formatPrice(product.list_price, product.currency)}</span>` : ""}
        <strong class="price-current">${formatPrice(product.current_price, product.currency)}</strong>
        ${product.discount_percent ? `<span class="discount-badge">-${product.discount_percent}%</span>` : ""}
      </div>
      <div class="meta">
        ${product.availability ? `<span>${escapeHtml(product.availability)}</span>` : ""}
        <span>${formatDate(product.last_price_checked_at)}</span>
      </div>
      <div class="row-actions">
        <button class="button action-button-small" data-action="open-product" data-id="${product.id}">Abrir Amazon</button>
        <button class="button action-button-small" data-action="copy-link" data-id="${product.id}">Copiar link</button>
        <button class="button primary action-button-small" data-action="open-message" data-id="${product.id}">Ver mensagem</button>
      </div>
    </article>
  `).join("");
}

function renderProductsTable() {
  const tbody = document.getElementById("products-table-body");
  const products = filteredProducts();

  if (!products.length) {
    tbody.innerHTML = `<tr><td colspan="6">Nenhum livro encontrado para os filtros atuais.</td></tr>`;
    return;
  }

  tbody.innerHTML = products.map((product) => `
    <tr class="product-row">
      <td class="book-cell">
        <strong>${escapeHtml(product.title)}</strong>
        <span>${escapeHtml(product.author || "Autor não informado")}</span>
      </td>
      <td>
        <strong>${escapeHtml(product.category)}</strong>
        <span class="subtext">${escapeHtml(product.subcategory || product.format_preference || "")}</span>
      </td>
      <td>${statusBadge(product)}</td>
      <td>${priceLabel(product)}</td>
      <td>${product.priority}</td>
      <td>
        <div class="row-actions compact-actions">
          <button class="button action-button-small" data-action="open-search" data-id="${product.id}" ${product.search_link ? "" : "disabled"}>Busca</button>
          <button class="button action-button-small" data-action="open-product" data-id="${product.id}" ${product.affiliate_link ? "" : "disabled"}>Amazon</button>
          <button class="button action-button-small" data-action="copy-link" data-id="${product.id}" ${product.affiliate_link ? "" : "disabled"}>Link</button>
          <button class="button action-button-small" data-action="open-message" data-id="${product.id}" ${product.needs_asin ? "disabled" : ""}>Msg</button>
          <button class="button action-button-small" data-action="toggle-asin-editor" data-id="${product.id}">ASIN</button>
          <button class="button action-button-small ${product.active ? "danger" : ""}" data-action="toggle-active" data-id="${product.id}">${product.active ? "Off" : "On"}</button>
        </div>
      </td>
    </tr>
    <tr class="asin-editor-row is-hidden" id="asin-row-${product.id}">
      <td colspan="6">
        <div class="asin-inline">
          <input id="asin-input-${product.id}" type="text" placeholder="Cole URL da Amazon ou ASIN correto">
          <button class="button primary action-button-small" data-action="save-asin" data-id="${product.id}">Salvar ASIN</button>
        </div>
      </td>
    </tr>
  `).join("");
}

function renderPendingProducts() {
  const container = document.getElementById("pending-list");
  const pending = state.products
    .filter((product) => product.needs_asin && product.active)
    .sort((a, b) => a.priority - b.priority || a.title.localeCompare(b.title));

  if (!pending.length) {
    container.innerHTML = `<div class="empty-state slim">Nenhum livro pendente de ASIN.</div>`;
    return;
  }

  container.innerHTML = pending.map((product) => `
    <article class="pending-card">
      <div class="pending-card__main">
        <h3>${escapeHtml(product.title)}</h3>
        <p>${escapeHtml(product.author || "Autor não informado")}</p>
        <span>${escapeHtml(product.category)} · P${product.priority}</span>
      </div>
      <p class="notes one-line">${escapeHtml(product.notes || "Sem observações.")}</p>
      <div class="pending-actions">
        <button class="button action-button-small" data-action="open-search" data-id="${product.id}" ${product.search_link ? "" : "disabled"}>Abrir busca</button>
        <input id="pending-asin-input-${product.id}" type="text" placeholder="URL ou ASIN">
        <button class="button primary action-button-small" data-action="save-asin" data-id="${product.id}" data-input="pending-asin-input-${product.id}">Salvar</button>
      </div>
    </article>
  `).join("");
}

function filteredProducts() {
  const search = getInputValue("filter-search").toLocaleLowerCase();
  const category = getInputValue("filter-category");
  const status = getInputValue("filter-status") || "all";
  const priority = getInputValue("filter-priority");
  const format = getInputValue("filter-format");

  return state.products.filter((product) => {
    const searchable = `${product.title} ${product.author || ""}`.toLocaleLowerCase();
    if (search && !searchable.includes(search)) return false;
    if (category && product.category !== category) return false;
    if (priority && String(product.priority) !== priority) return false;
    if (format && product.format_preference !== format) return false;
    if (status === "pending" && !product.needs_asin) return false;
    if (status === "link_ready" && (!isLinkReady(product) || isVerifiedPromotion(product))) return false;
    if (status === "price_unverified" && (!isLinkReady(product) || hasVerifiedPrice(product))) return false;
    if (status === "promotion" && !isVerifiedPromotion(product)) return false;
    if (status === "inactive" && product.active) return false;
    return true;
  });
}

function updateCategoryFilter() {
  const select = document.getElementById("filter-category");
  const previous = select.value;
  const categories = uniqueValues(state.products.map((product) => product.category));
  select.innerHTML = `<option value="">Categoria</option>${categories.map((category) => `<option value="${escapeAttr(category)}">${escapeHtml(category)}</option>`).join("")}`;
  select.value = categories.includes(previous) ? previous : "";
}

function updateFormatFilter() {
  const select = document.getElementById("filter-format");
  const previous = select.value;
  const formats = uniqueValues(state.products.map((product) => product.format_preference));
  select.innerHTML = `<option value="">Formato</option>${formats.map((format) => `<option value="${escapeAttr(format)}">${escapeHtml(format)}</option>`).join("")}`;
  select.value = formats.includes(previous) ? previous : "";
}

function applyQuickFilter(status) {
  const select = document.getElementById("filter-status");
  select.value = status;
  renderProductsTable();
  document.getElementById("monitored-books").scrollIntoView({ behavior: "smooth", block: "start" });
}

function clearFilters() {
  ["filter-search", "filter-category", "filter-status", "filter-priority", "filter-format"].forEach((id) => {
    const element = document.getElementById(id);
    if (!element) return;
    element.value = id === "filter-status" ? "all" : "";
  });
  renderProductsTable();
}

function scrollToLinksReady() {
  applyQuickFilter("link_ready");
}

function scrollToPending() {
  document.getElementById("pending-validation").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function refreshPrices() {
  const result = await apiFetch("/prices/refresh", {
    method: "POST",
    body: JSON.stringify({ only_ready: true }),
  });

  if (!result.live_prices_enabled) {
    showToast("Consulta real ainda não disponível. Configure a Creators API para atualizar preços automaticamente.", "error");
  } else {
    showToast(`${result.updated} preços atualizados.`, "success");
  }
  await refreshAll();
}

function openSearch(id) {
  const product = findProduct(id);
  if (!product?.search_link) {
    showToast("Produto sem link de busca.", "error");
    return;
  }
  window.open(product.search_link, "_blank", "noopener");
}

function openProduct(id) {
  const product = findProduct(id);
  if (!product?.affiliate_link) {
    showToast("Produto ainda não tem link afiliado.", "error");
    return;
  }
  window.open(product.affiliate_link, "_blank", "noopener");
}

async function copyAffiliateLink(productId) {
  const product = findProduct(productId);
  if (!product?.affiliate_link) {
    showToast("Produto ainda não tem link afiliado.", "error");
    return;
  }
  await copyText(product.affiliate_link);
  showToast("Link copiado", "success");
}

async function copyMessage(productId) {
  const payload = await apiFetch(`/manual-products/${productId}/message`);
  if (!payload.ready) {
    showToast("Produto ainda precisa de ASIN para gerar mensagem pública.", "error");
    return;
  }
  await copyText(payload.message);
  showToast("Mensagem copiada", "success");
}

async function openMessageModal(productId) {
  const product = findProduct(productId);
  const payload = await apiFetch(`/manual-products/${productId}/message`);
  if (!payload.ready) {
    showToast("Produto ainda precisa de ASIN para gerar mensagem pública.", "error");
    return;
  }

  state.openMessage = payload.message;
  setText("message-modal-title", product?.title || `Produto ${productId}`);
  document.getElementById("message-modal-content").textContent = payload.message;
  const modal = document.getElementById("message-modal");
  modal.classList.add("is-open");
  modal.setAttribute("aria-hidden", "false");
}

function closeMessageModal() {
  const modal = document.getElementById("message-modal");
  if (!modal) return;
  modal.classList.remove("is-open");
  modal.setAttribute("aria-hidden", "true");
}

async function copyOpenMessage() {
  if (!state.openMessage) {
    showToast("Nenhuma mensagem aberta.", "error");
    return;
  }
  await copyText(state.openMessage);
  showToast("Mensagem copiada", "success");
}

async function saveAsin(productId, value) {
  if (!value) {
    showToast("Cole uma URL da Amazon ou ASIN.", "error");
    return;
  }

  await apiFetch(`/manual-products/${productId}/asin`, {
    method: "PATCH",
    body: JSON.stringify({ amazon_url_or_asin: value }),
  });
  showToast("ASIN salvo com sucesso", "success");
  await refreshAll();
}

function toggleAsinEditor(productId) {
  const row = document.getElementById(`asin-row-${productId}`);
  if (!row) return;
  row.classList.toggle("is-hidden");
  const input = document.getElementById(`asin-input-${productId}`);
  if (!row.classList.contains("is-hidden") && input) input.focus();
}

async function toggleActive(productId) {
  const product = findProduct(productId);
  if (!product) return;

  await apiFetch(`/manual-products/${productId}/active`, {
    method: "PATCH",
    body: JSON.stringify({ active: !product.active }),
  });
  showToast(product.active ? "Produto inativado" : "Produto ativado", "success");
  await refreshAll();
}

async function copyAllReady() {
  const products = await apiFetch("/manual-products/ready");
  const blocks = [];

  for (const product of products) {
    const payload = await apiFetch(`/manual-products/${product.id}/message`);
    if (!payload.ready) continue;
    blocks.push(`==============================\nTítulo: ${product.title}\nAutor: ${product.author || ""}\nStatus: ${productStatus(product)}\n\n${payload.message}\n==============================`);
  }

  if (!blocks.length) {
    showToast("Nenhum link pronto para copiar.", "error");
    return;
  }

  await copyText(blocks.join("\n\n"));
  showToast("Mensagens copiadas", "success");
}

function statusBadge(product) {
  const status = productStatus(product);
  const className = status === "Promoção verificada"
    ? "promotion"
    : status === "Link pronto" || status === "Preço não verificado"
      ? "ready"
      : status === "Pendente de ASIN"
        ? "pending"
        : status === "Inativo"
          ? "inactive"
          : "neutral";
  return `<span class="status-badge ${className}">${status}</span>`;
}

function productStatus(product) {
  if (!product.active) return "Inativo";
  if (product.needs_asin) return "Pendente de ASIN";
  if (isVerifiedPromotion(product)) return "Promoção verificada";
  if (isLinkReady(product) && !hasVerifiedPrice(product)) return "Link pronto";
  if (isLinkReady(product)) return "Preço não verificado";
  return "Preço não verificado";
}

function isLinkReady(product) {
  return Boolean(product.active && !product.needs_asin && product.affiliate_link);
}

function hasVerifiedPrice(product) {
  return Boolean(
    product.current_price !== null &&
    product.current_price !== undefined &&
    product.last_price_checked_at,
  );
}

function isVerifiedPromotion(product) {
  return Boolean(
    isLinkReady(product) &&
    hasVerifiedPrice(product) &&
    ((product.discount_percent || 0) > 0 || (product.discount_amount || 0) > 0 || product.deal_badge),
  );
}

function priceLabel(product) {
  if (product.current_price !== null && product.current_price !== undefined) {
    return `<span class="price-current compact">${formatPrice(product.current_price, product.currency)}</span>`;
  }
  return `<span class="muted">Preço não verificado</span>`;
}

function findProduct(id) {
  return state.products.find((product) => product.id === id)
    || state.promotions.find((product) => product.id === id)
    || state.topItems.find((product) => product.id === id);
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value;
}

function getInputValue(id) {
  const element = document.getElementById(id);
  return element ? element.value.trim() : "";
}

function yesNo(value) {
  return value ? "Sim" : "Não";
}

function formatPrice(value, currency = "BRL") {
  if (value === null || value === undefined || value === "") return "Preço não verificado";
  const number = Number(value);
  if (Number.isNaN(number)) return "Preço não verificado";
  if ((currency || "BRL") === "BRL") {
    return number.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }
  return `${currency || ""} ${number.toFixed(2)}`.trim();
}

function formatDate(value) {
  if (!value) return "Nunca";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function copyText(text) {
  if (navigator.clipboard) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

function showToast(message, type = "info") {
  const stack = document.getElementById("toast-stack");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  stack.appendChild(toast);
  window.setTimeout(() => toast.remove(), 3600);
}

function uniqueValues(values) {
  return [...new Set(values.filter(Boolean))].sort((a, b) => a.localeCompare(b));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}
