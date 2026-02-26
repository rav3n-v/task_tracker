const el = {
  adminLoginWrap: document.getElementById('adminLoginWrap'),
  adminCreateWrap: document.getElementById('adminCreateWrap'),
  adminLoginForm: document.getElementById('adminLoginForm'),
  adminCreateUserForm: document.getElementById('adminCreateUserForm'),
  adminLogoutBtn: document.getElementById('adminLogoutBtn'),
  adminMessage: document.getElementById('adminMessage'),
};

async function request(url, options = {}) {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `Request failed: ${response.status}`);
  return data;
}

function renderAdminState(isAdmin) {
  el.adminLoginWrap.hidden = isAdmin;
  el.adminCreateWrap.hidden = !isAdmin;
}

async function bootstrap() {
  try {
    const status = await request('/api/admin/session');
    renderAdminState(Boolean(status.is_admin));
  } catch {
    renderAdminState(false);
  }

  el.adminLoginForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = new FormData(el.adminLoginForm);
    try {
      await request('/api/admin/login', {
        method: 'POST',
        body: JSON.stringify({
          username: form.get('username'),
          password: form.get('password'),
        }),
      });
      el.adminMessage.textContent = 'Admin authenticated.';
      el.adminLoginForm.reset();
      renderAdminState(true);
    } catch (error) {
      el.adminMessage.textContent = error.message;
    }
  });

  el.adminCreateUserForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = new FormData(el.adminCreateUserForm);
    try {
      await request('/api/register', {
        method: 'POST',
        body: JSON.stringify({
          username: form.get('username'),
          password: form.get('password'),
        }),
      });
      el.adminMessage.textContent = `Account ${form.get('username')} created.`;
      el.adminCreateUserForm.reset();
    } catch (error) {
      el.adminMessage.textContent = error.message;
    }
  });

  el.adminLogoutBtn.addEventListener('click', async () => {
    await request('/api/admin/logout', { method: 'POST' });
    renderAdminState(false);
    el.adminMessage.textContent = 'Admin logged out.';
  });
}

bootstrap();
