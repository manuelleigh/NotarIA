const API_BASE_URL = "http://127.0.0.1:5000";

async function handleResponse(response) {
  if (!response.ok) {
    const errorBody = await response.text(); // Leer el cuerpo para más contexto
    console.error("API Error Response:", errorBody);

    if (response.status === 401)
      throw new Error("Token de autenticación inválido o expirado.");
    if (response.status === 403)
      throw new Error("No tienes permiso para realizar esta acción.");
    if (response.status === 404)
      throw new Error("El recurso solicitado no fue encontrado.");

    throw new Error(`Error en la solicitud a la API: ${response.statusText}`);
  }
  return response.json();
}

export async function getChatHistory(apiKey) {
  const response = await fetch(`${API_BASE_URL}/chat/historial`, {
    headers: { Authorization: `Bearer ${apiKey}` },
  });
  const data = await handleResponse(response);
  return data.data;
}

export async function getChatDetail(chatId, apiKey) {
  const response = await fetch(`${API_BASE_URL}/chat/${chatId}`, {
    headers: { Authorization: `Bearer ${apiKey}` },
  });
  return handleResponse(response);
}

export async function sendChatMessage(mensaje, apiKey, chatId, nombre) {
  const body = { mensaje, chat_id: chatId, nombre };
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify(body),
  });
  return handleResponse(response);
}

export async function sendChatMessageStreaming(
  apiChatId,
  mensaje,
  apiKey,
  nombre,
  onChunk
) {
  const body = { mensaje, chat_id: apiChatId, nombre };

  const response = await fetch(`${API_BASE_URL}/chat/streaming`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify(body),
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value, { stream: true });
    if (onChunk) onChunk(chunk);
  }
}

export async function getContractDocument(chatId) {
  const response = await fetch(
    `${API_BASE_URL}/chat/documento?chat_id=${chatId}`
  );
  if (!response.ok) {
    const errorBody = await response.text();
    console.error("Error al obtener documento:", errorBody);
    if (response.status === 404)
      throw new Error("Documento o chat no encontrado.");
    throw new Error("Error al obtener el documento del contrato.");
  }
  // Devuelve el HTML como texto plano
  return response.text();
}
