-- CreateTable
CREATE TABLE "User" (
    "user_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "username" TEXT NOT NULL,
    "password" TEXT NOT NULL,
    "permission" INTEGER NOT NULL,
    "auth_method" TEXT NOT NULL
);

-- CreateTable
CREATE TABLE "Symptom" (
    "symptoms_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "name" TEXT NOT NULL,
    "academic" TEXT NOT NULL,
    "visit" INTEGER NOT NULL
);

-- CreateTable
CREATE TABLE "Bulletin" (
    "bulletin_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "class" TEXT NOT NULL,
    "user_id" INTEGER NOT NULL,
    "title" TEXT NOT NULL,
    "content" TEXT NOT NULL,
    "update_at" TEXT NOT NULL,
    "create_at" TEXT NOT NULL,
    CONSTRAINT "Bulletin_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "User" ("user_id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "Clinic" (
    "clinic_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "title" TEXT NOT NULL,
    "address" TEXT NOT NULL,
    "tel" TEXT NOT NULL,
    "tag" TEXT NOT NULL,
    "owner_id" INTEGER NOT NULL,
    CONSTRAINT "Clinic_owner_id_fkey" FOREIGN KEY ("owner_id") REFERENCES "User" ("user_id") ON DELETE RESTRICT ON UPDATE CASCADE
);
