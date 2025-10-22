Perfect ✅ Let’s extend your update log so you keep track of this new enhancement request.

---

## 🔄 Update Log – Bulk Upload & Admin Enhancements

### 📅 Date: *[insert today’s date]*

### 👤 Author: Abdulrahman

---

### **1. Bulk Upload – Class Readability (Done ✅)**

* Updated **student bulk upload** to accept **class names** (readable strings) in Excel instead of requiring class IDs.
* Parser checks if the `class` column is either:

  * a valid `SchoolClass.name` (string), or
  * a valid `SchoolClass.id` (integer).
* If the value doesn’t match, the row is skipped with a logged error.
* Removed the `class_id` field from `StudentUploadForm` to simplify workflow.

**Excel Example (Updated):**

```
student_id | first_name | last_name | email             | password | class
STU001     | John       | Doe       | john@example.com  | pass123  | SS2 Science
STU002     | Jane       | Smith     | jane@example.com  | pass456  | 3
```

---

### **2. Teacher Management – CRUD (Planned 🚧)**

* Add **update & delete functionality** for teachers in the admin panel.
* Admins should be able to:

  * Edit teacher details (name, email, teacher ID).
  * Deactivate/reactivate teacher accounts (`User.is_active`).
  * Delete teacher records (with safety checks to avoid orphaning subjects).

---

### **3. Teacher Listing – Filters & Search (Planned 🚧)**

* Add **filter options** to `/admin/teachers` route:

  * Search by **name** (first/last).
  * Search by **teacher ID**.
  * Search by **email**.
  * Filter by **active/inactive status**.
* Improve UI with a filter form (text inputs + dropdowns).
* Add **pagination** for scalability when number of teachers is large.
* Consider **sorting** (by last name, teacher ID, creation date).
* Optional: **Export filtered teacher list** to Excel/CSV.

---

### **Next Steps**

* Implement teacher CRUD routes & forms.
* Integrate filtering & pagination into `teachers.html`.
* Extend **teacher bulk upload** to allow **subject assignments** via Excel.

---

👉 Do you want me to also **add a planned update for student filters** (similar to teachers: by class, name, active status), since that will almost certainly be needed too?


| Entities                      | Relationship                   | Type | Through Table |
| ----------------------------- | ------------------------------ | ---- | ------------- |
| User ↔ Teacher / Student      | One-to-One                     | ✅    | —             |
| Teacher ↔ Exam                | One-to-Many                    | ✅    | —             |
| Exam ↔ Attempt                | One-to-Many                    | ✅    | —             |
| Student ↔ Attempt             | One-to-Many                    | ✅    | —             |
| **Student ↔ Exam**            | **Many-to-Many (via Attempt)** | ✅    | `attempts`    |
| Attempt ↔ Result              | One-to-One                     | ✅    | —             |
| Exam ↔ Subject / Class / Term | Many-to-One                    | ✅    | —             |
