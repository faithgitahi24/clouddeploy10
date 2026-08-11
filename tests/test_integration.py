def test_full_crud_flow(client):
    """Test the full CRUD flow from registration to deletion."""


    # 1. CREATE USER
    
    user_data = {
        "username": "integrationuser",
        "email": "integration@gmail.com",
        "password": "testpass123",
        "full_name": "Integration User"
    }

    register_response = client.post(
        "/register",
        json=user_data
    )

    assert register_response.status_code == 201

  
    # 2. LOGIN
   

    login_response = client.post(
        "/login",
        data={
            "username": user_data["username"],
            "password": user_data["password"]
        }
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {token}"
    }

    # 3. CREATE PRODUCT
   

    product_data = {
        "name": "Integration Product",
        "description": "Product created during integration test",
        "price": 100.00,
        "stock": 20
    }

    create_response = client.post(
        "/products",
        json=product_data,
        headers=headers
    )

    assert create_response.status_code == 201

    product_id = create_response.json()["id"]


    # 4. UPDATE PRODUCT
    

    update_data = {
        "name": "Updated Integration Product",
        "price": 150.00
    }

    update_response = client.patch(
        f"/products/{product_id}",
        json=update_data,
        headers=headers
    )

    assert update_response.status_code == 200

    updated_product = update_response.json()

    assert updated_product["name"] == "Updated Integration Product"
    assert updated_product["price"] == 150.00

  
    # 5. DELETE PRODUCT
    

    delete_response = client.delete(
        f"/products/{product_id}",
        headers=headers
    )

    assert delete_response.status_code == 204

    # Confirm product was deleted
    get_response = client.get(
        f"/products/{product_id}",
        headers=headers
    )

    assert get_response.status_code == 404