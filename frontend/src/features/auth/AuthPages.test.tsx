import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";
import { clearSession, getAccessToken } from "@/lib/auth/tokens";
import { renderApp } from "@/test/render";
import { server } from "@/test/server";
import { signInForTests, testAccessToken } from "@/test/session";

const tokens = () => ({
  token_type: "DPoP",
  access_token: testAccessToken(),
  expires_in: 600,
  refresh_token: "r1",
  session_id: "s1",
  return_to: null,
});

const loginFailed = () =>
  HttpResponse.json(
    { error: { code: "login_failed", message: "We couldn't sign you in." } },
    { status: 401 },
  );

describe("sign in", () => {
  it("asks the email, then the password, and goes back where it started", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("*/api/v1/auth/password/lookup", () =>
        HttpResponse.json({ exists: true, has_password: true }),
      ),
      http.post("*/api/v1/auth/password/login", () => HttpResponse.json(tokens())),
    );
    renderApp("/login?return_to=%2Ftrip");

    await user.type(await screen.findByLabelText("Email"), "pepe.perez@ejemplo.com");
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    expect(await screen.findByRole("heading", { name: "Ingresa tu contraseña" })).toBeInTheDocument();
    expect(screen.getByText("pepe.perez@ejemplo.com")).toBeInTheDocument();
    await user.type(screen.getByLabelText("Contraseña"), "una-clave-larga");
    await user.click(screen.getByRole("button", { name: "Ingresar" }));

    expect(await screen.findByRole("heading", { name: /Tu viaje/ })).toBeInTheDocument();
    expect(getAccessToken()).not.toBeNull();
  });

  it("says only «No pudimos iniciar sesión», whatever went wrong", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("*/api/v1/auth/password/lookup", () =>
        HttpResponse.json({ exists: true, has_password: true }),
      ),
      http.post("*/api/v1/auth/password/login", loginFailed),
    );
    renderApp("/login");

    await user.type(await screen.findByLabelText("Email"), "pepe.perez@ejemplo.com");
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    await user.type(await screen.findByLabelText("Contraseña"), "otra-clave");
    await user.click(screen.getByRole("button", { name: "Ingresar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("No pudimos iniciar sesión.");
    expect(screen.getByLabelText("Contraseña")).toHaveValue("");
  });

  it("sends an unknown email to «No encontramos una cuenta», with the option to create it", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("*/api/v1/auth/password/lookup", () =>
        HttpResponse.json({ exists: false, has_password: false }),
      ),
    );
    renderApp("/login");

    await user.type(await screen.findByLabelText("Email"), "pepe.peres@ejemplo.com");
    await user.click(screen.getByRole("button", { name: "Continuar" }));

    expect(
      await screen.findByRole("heading", { name: "No encontramos una cuenta con este email" }),
    ).toBeInTheDocument();
    expect(screen.getByText("pepe.peres@ejemplo.com")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Crear cuenta" })).toHaveAttribute(
      "href",
      expect.stringContaining("/signup?email=pepe.peres"),
    );
    expect(screen.getByRole("button", { name: "Probar con otro email" })).toBeInTheDocument();
  });

  it("shows only the organization's providers when it doesn't accept passwords", async () => {
    server.use(
      http.get("*/api/v1/auth/methods", () =>
        HttpResponse.json({
          organization_name: "Acme",
          password_enabled: false,
          signup_enabled: false,
          providers: [{ slug: "acme-sso", display_name: "Acme SSO" }],
        }),
      ),
    );
    renderApp("/login");

    expect(await screen.findByRole("button", { name: "Entrar con Acme SSO" })).toBeInTheDocument();
    expect(screen.getByText("Usa la cuenta que te dio Acme.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Email")).not.toBeInTheDocument();
    expect(screen.queryByText("Crea tu cuenta")).not.toBeInTheDocument();
  });

  it("takes the browser to the provider and waits with the button busy", async () => {
    const user = userEvent.setup();
    const assign = vi.fn();
    vi.stubGlobal("location", { ...window.location, assign, origin: window.location.origin });
    server.use(
      http.post("*/api/v1/auth/oidc/google/authorize", () =>
        HttpResponse.json({ authorization_url: "https://idp.test/auth?state=s1&code_challenge=c" }),
      ),
    );
    renderApp("/login?return_to=%2Ftrip");

    await user.click(await screen.findByRole("button", { name: "Continuar con Google" }));

    await waitFor(() =>
      expect(assign).toHaveBeenCalledWith("https://idp.test/auth?state=s1&code_challenge=c"),
    );
    expect(screen.getByRole("button", { name: "Te llevamos a Google…" })).toBeDisabled();
    expect(JSON.parse(sessionStorage.getItem("auth:oidc:s1") ?? "{}")).toMatchObject({
      provider: "google",
      returnTo: "/trip",
    });
  });

  it("explains why the session ended", async () => {
    await clearSession("revoked");
    renderApp("/login");

    expect(await screen.findByText("Cerramos tu sesión por seguridad.")).toBeInTheDocument();
  });
});

describe("back from the provider", () => {
  it("signs in and goes back to the trip", async () => {
    sessionStorage.setItem(
      "auth:oidc:s1",
      JSON.stringify({ provider: "google", providerName: "Google", returnTo: "/trip" }),
    );
    server.use(
      http.post("*/api/v1/auth/oidc/google/callback", () =>
        HttpResponse.json({ status: "signed_in", tokens: tokens() }),
      ),
    );
    renderApp("/auth/callback?code=c1&state=s1");

    expect(await screen.findByRole("heading", { name: /Tu viaje/ })).toBeInTheDocument();
  });

  it("without an account offers to create it, and then reminds the password email", async () => {
    const user = userEvent.setup();
    sessionStorage.setItem(
      "auth:oidc:s1",
      JSON.stringify({ provider: "google", providerName: "Google", returnTo: "/trip" }),
    );
    const notFound = {
      status: "account_not_found",
      attempt_id: "a1",
      email: "nuevo@ejemplo.com",
      display_name: "Nuevo",
      can_create: true,
    };
    server.use(
      http.post("*/api/v1/auth/oidc/google/callback", () => HttpResponse.json(notFound)),
      http.get("*/api/v1/auth/signup/pending/a1", () => HttpResponse.json(notFound)),
      http.post("*/api/v1/auth/signup/pending/a1", () =>
        HttpResponse.json({ ...tokens(), return_to: "/trip" }),
      ),
    );
    renderApp("/auth/callback?code=c1&state=s1");

    expect(
      await screen.findByRole("heading", { name: "No encontramos una cuenta con este email" }),
    ).toBeInTheDocument();
    expect(await screen.findByText("nuevo@ejemplo.com")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Crear cuenta" }));

    expect(await screen.findByText(/Te enviamos un correo para que crees una contraseña/)).toHaveTextContent(
      "sigue entrando con Google",
    );
  });

  it("goes back to the sign in with the one error if the provider failed", async () => {
    renderApp("/auth/callback?error=access_denied&state=desconocido");

    expect(await screen.findByRole("alert")).toHaveTextContent("No pudimos iniciar sesión.");
  });
});

describe("account from email", () => {
  it("signs up and waits to resend the verification email", async () => {
    const user = userEvent.setup();
    server.use(http.post("*/api/v1/auth/password/signup", () => new HttpResponse(null, { status: 202 })));
    renderApp("/signup?email=pepe.perez%40ejemplo.com");

    await user.type(await screen.findByLabelText("Nombre y apellido"), "Pepe Perez");
    await user.type(screen.getByLabelText("Contraseña"), "corta");
    expect(screen.getByText(/Al menos 10 caracteres/)).toHaveTextContent("○");
    await user.type(screen.getByLabelText("Contraseña"), "-y-larga");
    expect(screen.getByText(/Al menos 10 caracteres/)).toHaveTextContent("✓");
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "Crear cuenta" }));

    const status = await screen.findByRole("status");
    expect(within(status).getByRole("heading", { name: "Revisa tu correo" })).toBeInTheDocument();
    expect(within(status).getByRole("button", { name: /Reenviar el correo en/ })).toBeDisabled();
  });

  it("creates the first password from the email link", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("*/api/v1/auth/password/link", () =>
        HttpResponse.json({ email: "pepe.perez@ejemplo.com", kind: "set", signs_in_with: "Google" }),
      ),
      http.post("*/api/v1/auth/password/set", () => new HttpResponse(null, { status: 204 })),
    );
    renderApp("/account/password?token=t1&kind=set");

    expect(await screen.findByRole("heading", { name: "Crea tu contraseña" })).toBeInTheDocument();
    expect(screen.getByText(/Vas a poder seguir entrando también con Google/)).toBeInTheDocument();
    await user.type(screen.getByLabelText("Contraseña nueva"), "una-clave-larga");
    await user.click(screen.getByRole("button", { name: "Guardar contraseña" }));

    expect(await screen.findByRole("heading", { name: "Listo, ya tienes contraseña" })).toBeInTheDocument();
    // Without a session on this device it goes on to sign in, with the email already written.
    await user.click(screen.getByRole("link", { name: "Ingresar" }));
    expect(await screen.findByLabelText("Email")).toHaveValue("pepe.perez@ejemplo.com");
  });

  it("goes on with the session when the device already has one", async () => {
    const user = userEvent.setup();
    await signInForTests();
    server.use(
      http.post("*/api/v1/auth/password/link", () =>
        HttpResponse.json({ email: "pepe.perez@ejemplo.com", kind: "set", signs_in_with: "Google" }),
      ),
      http.post("*/api/v1/auth/password/set", () => new HttpResponse(null, { status: 204 })),
    );
    renderApp("/account/password?token=t1&kind=set");

    await user.type(await screen.findByLabelText("Contraseña nueva"), "una-clave-larga");
    await user.click(screen.getByRole("button", { name: "Guardar contraseña" }));

    expect(await screen.findByRole("link", { name: "Seguir" })).toHaveAttribute("href", "/");
  });

  it("offers a new link when the one opened no longer works", async () => {
    server.use(
      http.post("*/api/v1/auth/password/link", () =>
        HttpResponse.json({ error: { code: "invalid_link", message: "" } }, { status: 410 }),
      ),
    );
    renderApp("/account/password?token=viejo&kind=reset");

    expect(await screen.findByRole("heading", { name: "Este enlace ya no sirve" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Enviarme otro" })).toBeInTheDocument();
  });
});

describe("an organization's installation", () => {
  const acmeMethods = () =>
    server.use(
      http.get("*/api/v1/auth/methods", () =>
        HttpResponse.json({
          organization_name: "Acme",
          password_enabled: true,
          signup_enabled: false,
          providers: [{ slug: "acme-sso", display_name: "Acme SSO" }],
        }),
      ),
    );

  it("sends to the sign in before searching, without a session", async () => {
    acmeMethods();
    renderApp("/");

    expect(await screen.findByText("Usa la cuenta que te dio Acme.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Buscar" })).not.toBeInTheDocument();
  });

  it("closes every screen, not only searching", async () => {
    acmeMethods();
    renderApp("/account/devices");

    expect(await screen.findByText("Usa la cuenta que te dio Acme.")).toBeInTheDocument();
  });

  it("opens the screens of signing in and of the email links without a session", async () => {
    acmeMethods();
    renderApp("/login/forgot");

    expect(await screen.findByRole("heading", { name: "Elige una contraseña nueva" })).toBeInTheDocument();
  });

  it("goes back to the link that was opened once signed in", async () => {
    const user = userEvent.setup();
    acmeMethods();
    server.use(
      http.post("*/api/v1/auth/password/lookup", () =>
        HttpResponse.json({ exists: true, has_password: true }),
      ),
      http.post("*/api/v1/auth/password/login", () => HttpResponse.json(tokens())),
    );
    renderApp("/trip");

    await user.type(await screen.findByLabelText("Email"), "pepe.perez@acme.test");
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    await user.type(await screen.findByLabelText("Contraseña"), "una-clave-larga");
    await user.click(screen.getByRole("button", { name: "Ingresar" }));

    expect(await screen.findByRole("heading", { name: /Tu viaje/ })).toBeInTheDocument();
  });

  it("goes to its sign in after signing out", async () => {
    const user = userEvent.setup();
    acmeMethods();
    await signInForTests();
    server.use(http.post("*/api/v1/auth/logout", () => new HttpResponse(null, { status: 204 })));
    renderApp("/trip");

    await user.click(await screen.findByRole("button", { name: /Pepe/ }));
    await user.click(
      within(await screen.findByRole("menu")).getByRole("menuitem", { name: "Cerrar sesión" }),
    );

    expect(await screen.findByText("Usa la cuenta que te dio Acme.")).toBeInTheDocument();
  });

  it("lets its signed-in users search", async () => {
    acmeMethods();
    await signInForTests();
    renderApp("/");

    expect(await screen.findByRole("button", { name: "Buscar" })).toBeInTheDocument();
  });

  it("keeps searching public on the main platform", async () => {
    renderApp("/");

    expect(await screen.findByRole("button", { name: "Buscar" })).toBeInTheDocument();
  });
});

describe("account menu and devices", () => {
  it("shows «Ingresar» without a session", async () => {
    renderApp("/");

    expect(await screen.findAllByRole("link", { name: "Ingresar" })).not.toHaveLength(0);
  });

  it("shows the user's menu and signs out", async () => {
    const user = userEvent.setup();
    await signInForTests();
    server.use(http.post("*/api/v1/auth/logout", () => new HttpResponse(null, { status: 204 })));
    renderApp("/");

    await user.click(await screen.findByRole("button", { name: /Pepe/ }));
    const menu = await screen.findByRole("menu");
    expect(within(menu).getByText("pepe.perez@ejemplo.com")).toBeInTheDocument();
    await user.click(within(menu).getByRole("menuitem", { name: "Cerrar sesión" }));

    await waitFor(() => expect(getAccessToken()).toBeNull());
  });

  it("lists the devices and closes another one after confirming", async () => {
    const user = userEvent.setup();
    await signInForTests();
    const devices = [
      {
        id: "s1",
        device_name: "Chrome en Windows",
        created_at: "2026-10-12T10:00:00Z",
        last_seen_at: "2026-10-30T10:00:00Z",
        last_ip: "181.52.1.1",
        current: true,
      },
      {
        id: "s2",
        device_name: "Safari en iPhone",
        created_at: "2026-10-20T10:00:00Z",
        last_seen_at: "2026-10-29T10:00:00Z",
        last_ip: "190.1.1.1",
        current: false,
      },
    ];
    let closed = false;
    server.use(
      http.get("*/api/v1/me/sessions", () =>
        HttpResponse.json({ sessions: closed ? devices.slice(0, 1) : devices }),
      ),
      http.delete("*/api/v1/me/sessions/s2", () => {
        closed = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    renderApp("/account/devices");

    expect(await screen.findByText("Este dispositivo")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cerrar sesión" }));
    await user.click(
      within(screen.getByRole("alertdialog")).getByRole("button", { name: "Sí, cerrar sesión" }),
    );

    expect(await screen.findByText("Cerramos la sesión en Safari en iPhone.")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText("Safari en iPhone")).not.toBeInTheDocument());
  });
});
