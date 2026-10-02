/**
 * Create Example Second Brain Rules
 * 
 * This utility creates example rules to demonstrate the Second Brain feature
 * and help users understand how to use human-in-loop transformation.
 */

import { secondBrainService } from '@/services/secondBrainService';
import { CreateRuleRequest } from '@/types/secondBrain';

export function createExampleRules(): void {
  const exampleRules: CreateRuleRequest[] = [
    {
      title: "Customer tables should map to TMF Customer entity",
      description: "When analyzing tables that contain customer information, they should be mapped to TMF629 Customer entity",
      stage: "tmf-mapping",
      type: "field-mapping",
      priority: "high",
      context: {
        tables: ["Customer", "customer", "customers", "CUSTOMER"],
        fields: ["customer_id", "customer_name", "customer_email", "cust_id"],
        patterns: ["customer information", "client data"],
        scope: "global"
      },
      content: "Any table that contains customer information should be mapped to the TMF629 Customer entity. Look for key indicators like customer_id, customer_name, customer_email, customer_phone, or customer_address fields. Tables named 'Customer', 'Customers', 'Client', or 'Clients' are strong indicators. The Customer entity is a core entity in TMF629 and represents an individual or organization that has a relationship with the enterprise.",
      keywords: ["customer", "client", "tmf629", "entity mapping", "core entity"],
      examples: [
        "Table 'customers' with fields [customer_id, name, email, phone] → TMF629 Customer entity",
        "Table 'client_data' with fields [client_id, client_name, contact_info] → TMF629 Customer entity"
      ],
      tags: ["tmf629", "customer", "mapping", "core-entity"]
    },
    {
      title: "Contact information should map to ContactMedium entities",
      description: "Email, phone, and address fields should be mapped to appropriate TMF ContactMedium specializations",
      stage: "tmf-mapping", 
      type: "field-mapping",
      priority: "medium",
      context: {
        fields: ["email", "phone", "address", "contact", "telephone", "mobile"],
        patterns: ["contact information", "communication details"],
        scope: "global"
      },
      content: "Contact information should be mapped to TMF629 ContactMedium entities and their specializations. Email fields map to EmailContactMedium, phone fields map to PhoneContactMedium, addresses map to GeographicAddressContactMedium. Look for field names containing 'email', 'phone', 'address', 'contact', 'telephone', or 'mobile'. Each contact method should be treated as a separate ContactMedium instance.",
      keywords: ["contact", "email", "phone", "address", "contactmedium", "communication"],
      examples: [
        "email field → EmailContactMedium entity",
        "phone_number field → PhoneContactMedium entity", 
        "mailing_address field → GeographicAddressContactMedium entity"
      ],
      tags: ["tmf629", "contact", "communication", "contactmedium"]
    },
    {
      title: "ID fields should be validated for uniqueness",
      description: "Primary key and identifier fields must be validated for uniqueness constraints",
      stage: "validation",
      type: "validation-rule",
      priority: "critical",
      context: {
        fields: ["id", "key", "uuid", "identifier", "primary_key"],
        patterns: ["primary key", "unique identifier"],
        scope: "global"
      },
      content: "All ID fields and primary keys must be validated for uniqueness. This includes fields ending in '_id', '_key', or '_uuid', as well as fields explicitly named 'id', 'key', or 'identifier'. Check for duplicate values and ensure referential integrity. Primary keys should never be null or empty. Foreign keys should reference existing primary keys in related tables.",
      keywords: ["validation", "uniqueness", "primary key", "foreign key", "referential integrity"],
      examples: [
        "customer_id field should have unique values across all records",
        "product_uuid should not contain any duplicate UUIDs",
        "order_key should be validated for uniqueness and non-null values"
      ],
      tags: ["validation", "data-quality", "integrity", "primary-key"]
    },
    {
      title: "Date fields should be standardized to ISO format",
      description: "All date and timestamp fields should be converted to ISO 8601 format for consistency",
      stage: "output-generation",
      type: "transformation-logic", 
      priority: "medium",
      context: {
        fields: ["date", "time", "timestamp", "created", "updated", "modified"],
        patterns: ["date format", "timestamp", "temporal data"],
        scope: "global"
      },
      content: "All date and timestamp fields should be standardized to ISO 8601 format (YYYY-MM-DDTHH:mm:ss.sssZ). This includes fields containing 'date', 'time', 'created', 'updated', 'modified', or 'timestamp' in their names. Convert from common formats like MM/DD/YYYY, DD-MM-YYYY, or Unix timestamps. Ensure timezone information is preserved or standardized to UTC.",
      keywords: ["date", "timestamp", "iso8601", "standardization", "temporal"],
      examples: [
        "created_date '12/25/2023' → '2023-12-25T00:00:00.000Z'",
        "last_updated '2023-12-25 14:30:00' → '2023-12-25T14:30:00.000Z'",
        "Unix timestamp 1703519400 → '2023-12-25T14:30:00.000Z'"
      ],
      tags: ["transformation", "date", "standardization", "iso8601"]
    },
    {
      title: "Business partner data maps to Organization or Individual",
      description: "Business partner information should be classified and mapped to either Organization or Individual entities",
      stage: "raw-analysis",
      type: "data-interpretation",
      priority: "high",
      context: {
        tables: ["partner", "business_partner", "vendor", "supplier"],
        fields: ["partner_type", "business_type", "company_name", "individual_name"],
        patterns: ["business partner", "vendor information", "supplier data"],
        scope: "global"
      },
      content: "Business partner data should be analyzed and mapped to either TMF629 Organization entity (for companies) or Individual entity (for persons). Use indicators like company_name, business_registration, tax_id for Organizations. Use indicators like first_name, last_name, personal_id for Individuals. The partner_type or business_type field often contains explicit classification. Organizations should include additional fields like business registration numbers and tax identifiers.",
      keywords: ["business partner", "organization", "individual", "classification", "entity type"],
      examples: [
        "Partner with company_name and tax_id → Organization entity",
        "Partner with first_name and last_name → Individual entity",
        "Vendor with business_registration → Organization entity"
      ],
      tags: ["business-partner", "organization", "individual", "classification"]
    },
    {
      title: "Event tables should map to TMF Event entities",
      description: "Tables containing event or activity data should be mapped to appropriate TMF Event specializations",
      stage: "tmf-mapping",
      type: "field-mapping", 
      priority: "medium",
      context: {
        tables: ["event", "activity", "log", "audit", "transaction"],
        fields: ["event_type", "event_time", "activity_type", "action"],
        patterns: ["event data", "activity log", "audit trail"],
        scope: "global"
      },
      content: "Event and activity tables should be mapped to TMF629 Event entities or their specializations like CustomerCreateEvent, CustomerDeleteEvent, CustomerStateChangeEvent, or CustomerAttributeValueChangeEvent. Look for tables named 'event', 'activity', 'log', 'audit', or 'transaction'. Key fields include event_type, event_time, event_source, and event_data. Each event should have a timestamp and event type classification.",
      keywords: ["event", "activity", "audit", "log", "tmf event", "specialization"],
      examples: [
        "customer_events table → CustomerCreateEvent, CustomerDeleteEvent entities",
        "activity_log with action='update' → CustomerAttributeValueChangeEvent",
        "audit_trail table → appropriate Event specialization based on event_type"
      ],
      tags: ["events", "activities", "audit", "tmf629", "specialization"]
    }
  ];

  // Create the example rules
  exampleRules.forEach(rule => {
    try {
      secondBrainService.createRule(rule);
      console.log('✅ Created example rule:', rule.title);
    } catch (error) {
      console.error('❌ Failed to create example rule:', rule.title, error);
    }
  });

  console.log('🧠 Example Second Brain rules have been created!');
}

export function clearExampleRules(): void {
  // This would clear all rules - use carefully
  secondBrainService.clear();
  console.log('🧠 All Second Brain rules have been cleared!');
} 