import os
import openai as oai
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

import langchain_openai as lcai
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate, PromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnablePassthrough
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.tools.retriever import create_retriever_tool
from langchain_community.llms import HuggingFacePipeline

class mLlamaModel:
    """
    Wrapper for local Llama-3.1-8B-Instruct model using HuggingFace transformers.
    Provides a compatible interface with Azure OpenAI clients for easy migration.
    """
    def __init__(self, model_path="/srv/local/common_resources/models/Llama-3.1-8B-Instruct", temperature=0.1, max_new_tokens=512):
        print(f"Loading Llama model from {model_path}...")

        # Set HF cache directory if using shared models
        cache_dir = os.getenv("HF_HOME", "/srv/local/common_resources/models/transformers_cache")

        # Load tokenizer
        print("   Loading tokenizer...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            local_files_only=True,
            trust_remote_code=True
        )

        # Set pad token if not set
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # Load model - FORCE CPU due to CUDA kernel compatibility issues on server
        print("   Loading model weights (this may take 1-2 minutes)...")
        
        # Check if we should try GPU (set FORCE_CPU=true in env to disable GPU)
        force_cpu = os.getenv("FORCE_CPU", "false").lower() == "true"
        
        if not force_cpu and torch.cuda.is_available():
            try:
                print(f"   ✓ CUDA available - attempting GPU: {torch.cuda.get_device_name(0)}")
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_path,
                    torch_dtype=torch.float16,
                    device_map="auto",
                    low_cpu_mem_usage=True,
                    local_files_only=True,
                    trust_remote_code=True
                )
                # Test inference to make sure GPU actually works
                print("   Testing GPU inference...")
                test_input = self.tokenizer("Hello", return_tensors="pt").to(self.model.device)
                with torch.no_grad():
                    self.model.generate(**test_input, max_new_tokens=1)
                print("   ✓ GPU model loaded and tested successfully")
            except Exception as e:
                print(f"   ⚠️  GPU failed: {str(e)[:100]}")
                print("   ⚠️  Falling back to CPU...")
                # Clear GPU memory
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                force_cpu = True
        else:
            force_cpu = True
        
        if force_cpu:
            print("   📍 Loading model on CPU (this is slower but reliable)...")
            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=torch.float32,
                device_map="cpu",
                low_cpu_mem_usage=True,
                local_files_only=True,
                trust_remote_code=True
            )
            print("   ✓ CPU model loaded successfully")

        print("   Creating text generation pipeline...")
        
        # Define stop sequences to prevent over-generation
        stop_sequences = ["\n\nCategory:", "\nCategory:", "Category:", "\n\n\n"]
        
        # Create HuggingFace pipeline with stop sequences
        self.pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=temperature > 0,
            top_p=0.9,
            repetition_penalty=1.1,
            return_full_text=False,
            eos_token_id=self.tokenizer.eos_token_id,
        )

        # Wrap with LangChain's HuggingFacePipeline with stop sequences
        self.llm = HuggingFacePipeline(
            pipeline=self.pipe,
            pipeline_kwargs={"stop_sequence": stop_sequences[0]}  # Stop at first "Category:"
        )

        print("✓ Llama model loaded successfully")

    def get_llm(self):
        """Return the LangChain-compatible LLM instance"""
        return self.llm

class mOpenAI:
    """
    Already setup key and endpoint as environmental variables through bash.
    These can be found on Azure. Currently testing instance `vds-openai-test-001`.
    """
    def __init__(self):
        self.client = oai.AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2023-12-01-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.deployment_name = 'TEST'  # This will correspond to the custom name you chose for your deployment when you deployed a model. Use a gpt-35-turbo-instruct deployment.

    def demo(self, start_phrase='Write a tagline for an ice cream shop for orcs.', token_lim=15):
        # Send a completion call to generate an answer
        print('Sending a test completion job')
        response = self.client.completions.create(model=self.deployment_name, prompt=start_phrase, max_tokens=token_lim)
        print(start_phrase + response.choices[0].text)

class mLangChain:
    def __init__(self,mlimit=100):
        self.client_completion = lcai.AzureOpenAI(
            openai_api_key=os.getenv("AZURE_OPENAI_KEY"),
            openai_api_version="2024-02-15-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            deployment_name="TEST",
            model_name="gpt-3.5-turbo-instruct",
        )
        self.client_agent = lcai.AzureChatOpenAI(
            openai_api_key=os.getenv("AZURE_OPENAI_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_deployment="NUHAI-GPT4",
            openai_api_version="2024-02-15-preview",
            model_name="gpt-4",
        )
        self.embeddings = lcai.AzureOpenAIEmbeddings(
            openai_api_key=os.getenv("AZURE_OPENAI_KEY"),
            openai_api_version="2024-02-15-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            deployment="TEST-Embedding",
        )
        self.qa_prompt = ChatPromptTemplate.from_messages([
            ("system", "Your vocabulary is limited to a 5 year old american."),
            ("user", "{input}")
        ])
        self.prompt_limit = mlimit

    def set_prompt_limit(self, limit):
        self.prompt_limit = limit

    def set_prompt(self, system, user):
        self.qa_prompt = ChatPromptTemplate.from_messages([
            ("system", system),
            ("user", user)
        ])

    def set_context(self, docs):
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        self.documents = self.text_splitter.split_documents(docs)
        self.vector = FAISS.from_documents(self.documents, self.embeddings)
        self.document_chain = create_stuff_documents_chain(self.client_completion, self.qa_prompt)
        self.retriever = self.vector.as_retriever()
        self.retrieval_chain = create_retrieval_chain(self.retriever, self.document_chain)

    def set_chain_history(self):
        self.contextualize_history_system_prompt = """
        Given a chat history and the latest user question \
        which might reference context in the chat history, formulate a standalone question \
        which can be understood without the chat history. Do NOT answer the question, \
        just reformulate with context from history if needed OR ELSE return it as is.\
        
        Chat history = {chat_history} \
        Question = {input} \
        
        Reformulate the question.
        """
        self.contextualize_history_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.contextualize_history_system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("user", "{input}"),
            ]
        )
        self.history_chain = self.contextualize_history_prompt | self.client_completion


    def set_agent(self, name="<tool>", description="<desc>", system='You are a helpful assistant', input='{input}'):
        tool = create_retriever_tool(
            self.retriever,
            name,
            description,
        )

        self.tools = [tool]
        self.agent_template = ChatPromptTemplate.from_messages(
                [
                    ("system", system),
                    # MessagesPlaceholder("chat_history", optional=True),
                    ("human", input),
                    MessagesPlaceholder("agent_scratchpad"),
                ]
            )

    def demo(self, start_phrase='Write a tagline for an ice cream shop for orcs.', token_lim=15):
        # Send a completion call to generate an answer
        print('Sending a test completion job')
        # response = self.client(start_phrase)
        response = self.client_completion.invoke(start_phrase)

        print(start_phrase + response)

    def demo_chain(self, start_phrase=None):
        chain = self.qa_prompt | self.client_completion
        response = chain.invoke({"input": start_phrase})

        print(start_phrase + response)

    def demo_chain_context(self, start_phrase=None):
        response = self.retrieval_chain.invoke({"input": start_phrase})
        print(start_phrase + response["answer"])


    def demo_chain_history(self,start_phrase=None):
        response = self.history_chain.invoke(
            {
                "chat_history": [
                    HumanMessage(content="What is Three Kings on Reddit?"),
                    AIMessage(content="""
                    Three Kings on Reddit is a ritual that involves setting up a room with specific items and sitting in a specific position at 3:30 AM. 
                    It is said to allow access to a place called the 'Shadowside', but it is important to follow all instructions and be mentally and spiritually stable before attempting it.
                    """),
                ],
                "input": start_phrase,
            }
        )
        print(start_phrase + response["answer"])

    def demo_rag(self):
        rag_chain = (
                RunnablePassthrough.assign(
                    context=self.history_chain | self.retriever
                )
                | self.qa_prompt
                | self.client_completion
        )

        chat_history = []
        turn = 0
        print("Ask questions about Three Kings:")
        while(True):
            start_phrase=input("User: ")
            if start_phrase=="exit":
                print("System: OK, bye.")
                break
            if turn==self.prompt_limit:
                print("System: Reached local prompt limit, Bye.")
                break
            ai_msg = rag_chain.invoke({"input": start_phrase, "chat_history": chat_history})
            print(ai_msg)
            chat_history.extend([HumanMessage(content=start_phrase), AIMessage(content=ai_msg)])
            turn = turn + 1
            print()

    def demo_agent(self, init_phrase="Hi, I am an agent who can help you understand Three Kings:"):
        self.agent = create_openai_tools_agent(self.client_agent, self.tools, self.agent_template)
        self.agent_executor = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True)

        turn = 0
        chat_history = []
        print(init_phrase)
        while(True):
            start_phrase = input("User: ")
            if start_phrase=="exit":
                print("System: OK, bye.")
                break
            if turn==self.prompt_limit:
                print("System: Reached local prompt limit, Bye.")
                break
            result = self.agent_executor.invoke({"input": start_phrase, "chat_history": chat_history})
            print(result["output"])
            chat_history.extend([HumanMessage(content=start_phrase), AIMessage(content=result["output"])])
            turn = turn + 1
