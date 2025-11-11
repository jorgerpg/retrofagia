(function () {
  const body = document.body;
  if (!body) {
    return;
  }

  initFlashDismissal();

  const isAuthenticated = body.dataset.authenticated === "true";
  if (!isAuthenticated) {
    return;
  }

  const origin = window.location.origin;
  const followBadge = document.querySelector('[data-notification="follow"]');
  const followNavItem = followBadge ? followBadge.closest(".bottom-nav-item") : null;
  const messageBadge = document.querySelector('[data-notification="message"]');
  const messageNavItem = messageBadge ? messageBadge.closest(".bottom-nav-item") : null;
  const chatPage = setupChat();

  let lastNotificationCheck = new Date().toISOString();
  let notificationController = null;
  let notificationsPaused = false;
  let notificationRetryHandle = null;

  function setBadge(badgeEl, parentEl, count) {
    if (!badgeEl || !parentEl) {
      return;
    }

    if (count > 0) {
      badgeEl.textContent = count > 9 ? "9+" : String(count);
      parentEl.classList.add("has-notification");
    } else {
      badgeEl.textContent = "";
      parentEl.classList.remove("has-notification");
    }
  }

  function requestNotifications(waitForUpdates) {
    if (notificationsPaused) {
      return;
    }

    if (notificationRetryHandle) {
      clearTimeout(notificationRetryHandle);
      notificationRetryHandle = null;
    }

    const url = new URL("/api/notifications", origin);
    if (lastNotificationCheck) {
      url.searchParams.set("since", lastNotificationCheck);
    }
    if (waitForUpdates) {
      url.searchParams.set("wait", "1");
      url.searchParams.set("timeout", "30");
    }

    const controller = new AbortController();
    notificationController = controller;

    fetch(url.toString(), {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
      signal: controller.signal,
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error("Erro ao buscar notificações");
        }
        return response.json();
      })
      .then((data) => {
        notificationController = null;
        lastNotificationCheck = data.server_time || new Date().toISOString();
        const followerCount = Array.isArray(data.new_followers)
          ? data.new_followers.length
          : 0;
        const newMessages = Array.isArray(data.new_messages)
          ? data.new_messages
          : [];

        setBadge(followBadge, followNavItem, followerCount);
        setBadge(messageBadge, messageNavItem, newMessages.length);

        if (
          chatPage &&
          newMessages.some(
            (item) =>
              item &&
              item.from_user &&
              safeNumber(item.from_user.id) === chatPage.selectedUserId,
          )
        ) {
          chatPage.refreshNow();
        }

        requestNotifications(true);
      })
      .catch((error) => {
        notificationController = null;
        if (notificationsPaused) {
          return;
        }
        if (error.name === "AbortError") {
          requestNotifications(true);
          return;
        }
        scheduleNotificationRetry();
      });
  }

  function scheduleNotificationRetry() {
    if (notificationsPaused) {
      return;
    }
    if (notificationRetryHandle) {
      clearTimeout(notificationRetryHandle);
    }
    notificationRetryHandle = window.setTimeout(() => {
      notificationRetryHandle = null;
      requestNotifications(true);
    }, 4000);
  }

  function pauseNotifications() {
    notificationsPaused = true;
    if (notificationRetryHandle) {
      clearTimeout(notificationRetryHandle);
      notificationRetryHandle = null;
    }
    if (notificationController) {
      notificationController.abort();
      notificationController = null;
    }
  }

  function resumeNotifications() {
    if (!notificationsPaused) {
      return;
    }
    notificationsPaused = false;
    requestNotifications(false);
  }

  requestNotifications(false);

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      pauseNotifications();
      if (chatPage && chatPage.onVisibilityChange) {
        chatPage.onVisibilityChange();
      }
    } else {
      resumeNotifications();
      if (chatPage && chatPage.onVisibilityChange) {
        chatPage.onVisibilityChange();
      }
    }
  });

  window.addEventListener("beforeunload", () => {
    pauseNotifications();
    if (chatPage && chatPage.dispose) {
      chatPage.dispose();
    }
  });

  function initFlashDismissal() {
    const flashContainer = document.querySelector(".flash-container");
    if (!flashContainer) {
      return;
    }

    const flashes = flashContainer.querySelectorAll(".flash");
    if (!flashes.length) {
      flashContainer.remove();
      return;
    }

    flashes.forEach((flash) => {
      window.setTimeout(() => {
        flash.classList.add("flash-dismissed");
        window.setTimeout(() => {
          flash.remove();
          if (!flashContainer.querySelector(".flash")) {
            flashContainer.remove();
          }
        }, 220);
      }, 1000);
    });
  }

  function setupChat() {
    const thread = document.querySelector(
      "[data-chat-thread][data-selected-user-id]",
    );
    if (!thread) {
      return null;
    }

    const messagesContainer = thread.querySelector("[data-chat-messages]");
    if (!messagesContainer) {
      return null;
    }

    const selectedUserId = safeNumber(thread.dataset.selectedUserId);
    if (!selectedUserId) {
      return null;
    }

    let lastMessageId = safeNumber(thread.dataset.lastMessageId);
    let messageController = null;
    let messageRetryHandle = null;
    let forceImmediateAfterAbort = false;
    let pollingPaused = false;

    function ensureScroll() {
      window.requestAnimationFrame(() => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
      });
    }

    function removeEmptyState() {
      const emptyState = messagesContainer.querySelector(".muted");
      if (emptyState) {
        emptyState.remove();
      }
    }

    function renderMessage(message) {
      const wrapper = document.createElement("div");
      wrapper.className = "message " + (message.from_me ? "from-me" : "from-them");
      wrapper.dataset.messageId = String(message.id);

      const content = document.createElement("p");
      content.textContent = message.content;

      const timestamp = document.createElement("span");
      timestamp.className = "timestamp";
      timestamp.textContent = formatTimestamp(message.created_at);

      wrapper.append(content, timestamp);
      return wrapper;
    }

    function appendMessages(messages) {
      if (!Array.isArray(messages) || messages.length === 0) {
        return;
      }

      removeEmptyState();

      messages.forEach((message) => {
        const numericId = safeNumber(message && message.id);
        if (!numericId) {
          return;
        }

        const exists = messagesContainer.querySelector(
          '[data-message-id="' + numericId + '"]',
        );
        if (exists) {
          return;
        }

        const payload = {
          id: numericId,
          from_me: Boolean(message.from_me),
          content: message.content || "",
          created_at: message.created_at,
        };

        messagesContainer.appendChild(renderMessage(payload));
        lastMessageId = Math.max(lastMessageId, numericId);
      });

      ensureScroll();
    }

    function clearMessageRetry() {
      if (messageRetryHandle) {
        clearTimeout(messageRetryHandle);
        messageRetryHandle = null;
      }
    }

    function scheduleMessageRetry() {
      if (pollingPaused) {
        return;
      }
      clearMessageRetry();
      messageRetryHandle = window.setTimeout(() => {
        messageRetryHandle = null;
        startLongPoll(true);
      }, 4000);
    }

    function startLongPoll(waitForUpdates) {
      if (pollingPaused) {
        return;
      }

      clearMessageRetry();

      const url = new URL(`/api/chat/${selectedUserId}/messages`, origin);
      url.searchParams.set("after", String(lastMessageId));
      if (waitForUpdates) {
        url.searchParams.set("wait", "1");
        url.searchParams.set("timeout", "30");
      }

      const controller = new AbortController();
      messageController = controller;

      fetch(url.toString(), {
        headers: { Accept: "application/json" },
        credentials: "same-origin",
        signal: controller.signal,
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error("Erro ao buscar mensagens");
          }
          return response.json();
        })
        .then((data) => {
          messageController = null;
          if (Array.isArray(data.messages)) {
            appendMessages(data.messages);
          }
          if (typeof data.last_id === "number" && data.last_id > lastMessageId) {
            lastMessageId = data.last_id;
          }
          startLongPoll(true);
        })
        .catch((error) => {
          messageController = null;
          if (pollingPaused) {
            return;
          }
          if (error.name === "AbortError") {
            if (forceImmediateAfterAbort) {
              forceImmediateAfterAbort = false;
              startLongPoll(false);
            } else {
              startLongPoll(true);
            }
            return;
          }
          scheduleMessageRetry();
        });
    }

    function forceRefresh() {
      pollingPaused = false;
      forceImmediateAfterAbort = true;
      clearMessageRetry();
      if (messageController) {
        messageController.abort();
      } else {
        startLongPoll(false);
      }
    }

    function pausePolling() {
      pollingPaused = true;
      clearMessageRetry();
      if (messageController) {
        messageController.abort();
        messageController = null;
      }
    }

    function resumePolling() {
      if (!pollingPaused) {
        forceRefresh();
        return;
      }
      pollingPaused = false;
      forceRefresh();
    }

    function dispose() {
      pausePolling();
    }

    ensureScroll();
    startLongPoll(true);

    return {
      selectedUserId,
      refreshNow: forceRefresh,
      onVisibilityChange: () => {
        if (document.visibilityState === "hidden") {
          pausePolling();
        } else {
          resumePolling();
        }
      },
      dispose,
    };
  }

  function formatTimestamp(isoString) {
    if (!isoString) {
      return "";
    }
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) {
      return "";
    }
    const pad = (value) => String(value).padStart(2, "0");
    return `${pad(date.getDate())}/${pad(date.getMonth() + 1)} ${pad(
      date.getHours(),
    )}:${pad(date.getMinutes())}`;
  }

  function safeNumber(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }
})();
