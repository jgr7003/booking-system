import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { renderApp } from "@/test/render";

describe("search form", () => {
  it("suggests cities and airports and picks one with the keyboard", async () => {
    const user = userEvent.setup();
    renderApp("/");

    const origin = await screen.findByRole("combobox", { name: "Origen" });
    await user.type(origin, "new y");

    const list = await screen.findByRole("listbox", { name: "Sugerencias para origen" });
    // Suggestions arrive after the 200 ms debounce and the request.
    expect(
      await within(list).findByRole("option", { name: /New York · todos los aeropuertos/ }),
    ).toBeInTheDocument();

    await user.keyboard("{Enter}");

    expect(origin).toHaveValue("New York · todos los aeropuertos");
    expect(screen.getByText("NYC")).toBeInTheDocument();
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("each infant needs a different adult", async () => {
    const user = userEvent.setup();
    renderApp("/");

    await user.click(await screen.findByRole("button", { name: /Pasajeros/ }));
    await user.click(screen.getByRole("button", { name: /Agregar menor/ }));
    await user.selectOptions(screen.getByRole("combobox", { name: "Menor 1" }), "0");
    await user.click(screen.getByRole("button", { name: /Agregar menor/ }));

    const second = screen.getByRole("combobox", { name: "Menor 2" });
    expect(within(second).getByRole("option", { name: "Menos de 1 año" })).toBeDisabled();
    expect(within(second).getByRole("option", { name: "5 años" })).toBeEnabled();
    expect(screen.getByText(/en brazos de un adulto distinto/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Agregar adulto" }));
    expect(within(second).getByRole("option", { name: "Menos de 1 año" })).toBeEnabled();
  });

  it("validates before searching", async () => {
    const user = userEvent.setup();
    renderApp("/");

    await user.click(await screen.findByRole("button", { name: "Buscar" }));

    expect(screen.getByText("Elegí el origen.")).toBeInTheDocument();
    expect(screen.getByText("Elegí el destino.")).toBeInTheDocument();
    expect(screen.getByText("Elegí la fecha de ida.")).toBeInTheDocument();
  });
});
