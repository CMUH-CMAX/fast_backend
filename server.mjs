// Import the framework and instantiate it
import Fastify from 'fastify'
import { PrismaClient } from '@prisma/client'
import { v4 as uuidv4 } from 'uuid';

const prisma = new PrismaClient()

const fastify = Fastify({
  logger: true
})

let user_session_buffer = {};

async function get_userprofile_by_uuid( uuid ) {
    let user_id = user_session_buffer[uuid].user_id
    const profile = await prisma.userProfile.findFirst({
        where: {
            user_id: user_id,
        },
    })
    return profile
}

async function get_user_by_auth( username, password ) {
    const user = await prisma.users.findFirst({
        where: { username, password },
    });
    return user;
}

async function create_user( username, password, permission, auth_method ) {
    //throw new Error('Not implemented');
    const user = await prisma.users.create({
        data: { username, password, permission, auth_method },
    });
    // create user profile
    await prisma.userProfile.create({
        data: { gender: "gay", brithday: new Date(), user: { connect: { user_id: user.user_id } } },
    });
    console.log(user);
}

fastify.get('/api/v1/user/:uuid', async function handler (request, reply) {
    let { uuid } = request.params;
    let result;
    try{
        result = await get_userprofile_by_uuid( uuid );
        console.log(result);
        return result;
    }catch(err){
        console.error(err);
        return {"message": "Error", err}
    }
    // example command: curl http://localhost:3000/api/v1/user/123 -X GET
})

fastify.post('/api/v1/user', async function handler (request, reply) {
    let { username, password } = request.body;
    let result;
    try{
        result = await create_user( username, password, 0, 'local' );
        return {"message": "Success"};
    }catch(err){
        console.error(err);
        return {"message": "Error", err}
    }
    // example command: curl http://localhost:3000/api/v1/user -X POST -H "Content-Type: application/json" -d '{"username": "test", "password": "test"}'
})

fastify.post('/api/v1/user/session', async function handler (request, reply) {
    let { username, password } = request.body;
    let result;
    try{
        let uuid = uuidv4();
        result = await get_user_by_auth( username, password );
        user_session_buffer[uuid] = result;
        return {"uuid": uuid};
    }catch(err){
        console.error(err);
        return {"message": "Error", err}
    }
    // example command: curl http://localhost:3000/api/v1/user/session -X POST -H "Content-Type: application/json" -d '{"username": "test", "password": "test"}'
})

// Run the server!
try {
  await fastify.listen({ port: 3000 })
} catch (err) {
  fastify.log.error(err)
  process.exit(1)
}
