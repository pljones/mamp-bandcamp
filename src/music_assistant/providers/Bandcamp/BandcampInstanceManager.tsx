import React, { useState, useEffect } from "react";

const BandcampInstanceManager = () => {
  const [instances, setInstances] = useState([]);
  const [formState, setFormState] = useState({ instance_id: "", domain: "", username: "", password: "" });

  useEffect(() => {
    fetch("/api/bandcamp/instances")
      .then((response) => response.json())
      .then((data) => setInstances(data));
  }, []);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormState({ ...formState, [name]: value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const method = formState.instance_id ? "PUT" : "POST";
    fetch(`/api/bandcamp/instances/${formState.instance_id || ""}`, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formState),
    }).then(() => {
      // Refresh instances
      fetch("/api/bandcamp/instances")
        .then((response) => response.json())
        .then((data) => setInstances(data));
    });
  };

  const handleDelete = (instance_id) => {
    fetch(`/api/bandcamp/instances/${instance_id}`, { method: "DELETE" }).then(() => {
      // Refresh instances
      fetch("/api/bandcamp/instances")
        .then((response) => response.json())
        .then((data) => setInstances(data));
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
          required
        />
        <input
          type="password"
          name="password"
          placeholder="Password"
          value={formState.password}
          onChange={handleInputChange}
          required
        />
        <button type="submit">Save</button>
      </form>
    </div>
  );
};

export default BandcampInstanceManager;