import React, { useState, useEffect } from "react";

const BandcampInstanceManager = () => {
  const [instances, setInstances] = useState([]);
  const [formState, setFormState] = useState({
    instance_id: "",
    domain: "",
    username: "",
    password: "",
    auth_type: "credentials", // Default to credentials
    auth_token: "", // For cookie-based authentication
  });

  useEffect(() => {
    // Fetch the list of existing instances from the backend
    fetch("/api/bandcamp/instances")
      .then((response) => response.json())
      .then((data) => setInstances(data));
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormState({ ...formState, [name]: value });
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const method = formState.instance_id ? "PUT" : "POST";
    
    fetch(`/api/bandcamp/instances/${formState.instance_id || ""}`, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formState),
    }).then(() => {
      // Refresh the list of instances
      fetch("/api/bandcamp/instances")
        .then((response) => response.json())
        .then((data) => setInstances(data));
    });
  };

  const handleDelete = (instance_id: string) => {
    fetch(`/api/bandcamp/instances/${instance_id}`, { method: "DELETE" }).then(() => {
      // Refresh the list of instances
      fetch("/api/bandcamp/instances")
        .then((response) => response.json())
        .then((data) => setInstances(data));
    });
  };

  const handleTestAuthentication = () => {
    fetch(`/api/bandcamp/instances/${formState.instance_id}/auth/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ auth_type: formState.auth_type }),
    })
      .then((response) => {
        if (response.ok) {
          alert("Authentication successful!");
        } else {
          alert("Authentication failed!");
        }
      })
      .catch(() => {
        alert("Error testing authentication.");
      });
  };

  return (
    <div>
      <h2>Bandcamp Instances</h2>
      <ul>
        {instances.map((instance) => (
          <li key={instance.instance_id}>
            {instance.instance_id} ({instance.domain})
            <button onClick={() => setFormState(instance)}>Edit</button>
            <button onClick={() => handleDelete(instance.instance_id)}>Delete</button>
          </li>
        ))}
      </ul>

      <h3>{formState.instance_id ? "Edit Instance" : "Add Instance"}</h3>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          name="instance_id"
          placeholder="Instance ID"
          value={formState.instance_id}
          onChange={handleInputChange}
          required
        />
        <input
          type="text"
          name="domain"
          placeholder="Domain"
          value={formState.domain}
          onChange={handleInputChange}
          required
        />
        <input
          type="text"
          name="username"
          placeholder="Username"
          value={formState.username}
          onChange={handleInputChange}
        />
        <input
          type="password"
          name="password"
          placeholder="Password"
          value={formState.password}
          onChange={handleInputChange}
        />
        <input
          type="text"
          name="auth_token"
          placeholder="Auth Token (for cookies)"
          value={formState.auth_token}
          onChange={handleInputChange}
        />
        <select
          name="auth_type"
          value={formState.auth_type}
          onChange={handleInputChange}
        >
          <option value="credentials">Credentials</option>
          <option value="cookies">Cookies</option>
        </select>
        <button type="submit">Save</button>
        <button type="button" onClick={handleTestAuthentication}>
          Test Authentication
        </button>
      </form>
    </div>
  );
};

export default BandcampInstanceManager;