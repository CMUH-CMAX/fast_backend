import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
/*
model User {
  user_id     Int     @id @default(autoincrement())
  username    String
  password    String
  permission  Int
  auth_method String
}
*/
    const user = await prisma.user.create({
        data: {
            username: 'admin',
            password: 'SecretPassword',
            permission: 0,
            auth_method: 'local',
        },
    })
    console.log(user)

    // ... you will write your Prisma Client queries here
}

main()
    .then(async () => {
        await prisma.$disconnect()
    })
    .catch(async (e) => {
        console.error(e)
        await prisma.$disconnect()
        process.exit(1)
    })
